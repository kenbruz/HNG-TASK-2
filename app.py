from flask import Flask, jsonify, request, send_file
from sqlalchemy import String, Integer, Float, Column, text, create_engine, DateTime, func
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv
import requests
from os import environ
import os
import random
from datetime import datetime, timezone
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

load_dotenv()
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_PORT = os.getenv("DB_PORT")

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

# ------ Create DB
root_engine = create_engine(f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}")
with root_engine.connect() as conn:
    conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}"))

# ------ Connect to DB
engine = create_engine(f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}")
Base = declarative_base()

SQLALCHEMY_DATABASE_URI = (
    f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")


class CountryData(Base):
    __tablename__ = "countrydata"
    id = Column(Integer, primary_key=True, autoincrement=True)  # — auto - generated
    name = Column(String(250), unique=True, nullable=False)  # — required
    capital = Column(String(250))  # — optional
    region = Column(String(250))  # — optional
    population = Column(Integer)  # — required
    currency_code = Column(String(250))  # — required
    exchange_rate = Column(Float)  # — required
    estimated_gdp = Column(Float)  # — computed from population × random(1000–2000) ÷ exchange_rate
    flag_url = Column(String(250))  # — optional


class Refresh(Base):
    __tablename__ = "refresh"
    id = Column(Integer, primary_key=True, autoincrement=True)
    last_refreshed_at = Column(DateTime)


# ------ Create Tables
Base.metadata.create_all(engine)

# Create session
Session = sessionmaker(bind=engine)
session = Session()


def generate_summary_image(session):
    """Generate cache/summary.pngstats."""
    os.makedirs("cache", exist_ok=True)

    total_countries = session.query(CountryData).count()

    # Top 5 countries by GDP
    top_5 = session.query(CountryData).order_by(CountryData.estimated_gdp.desc()).limit(5).all()

    # Last refresh timestamp
    refresh_entry = session.query(Refresh).first()
    last_refresh = refresh_entry.last_refreshed_at if refresh_entry else "N/A"

    # Prepare data for chart
    names = [c.name for c in top_5]
    gdps = [c.estimated_gdp for c in top_5]

    plt.figure(figsize=(8, 5))
    plt.barh(names, gdps)
    plt.xlabel("Estimated GDP")
    plt.title(f"Top 5 Countries by Estimated GDP\nTotal: {total_countries} | Refreshed: {last_refresh}")
    plt.tight_layout()

    plt.savefig("cache/summary.png")
    plt.close()


# Endpoints
@app.route("/countries/refresh", methods=["POST"])
def fetch_countries():
    response = requests.get("https://restcountries.com/v2/all?fields=name,capital,region,population,flag,currencies")
    if response.status_code != 200:
        return jsonify({"error": "External data source unavailable",
                        "details": "Could not fetch data from Restcoutries API"}), 503
    country_data = response.json()

    rate_resp = requests.get("https://open.er-api.com/v6/latest/USD")
    if rate_resp.status_code != 200:
        return jsonify({"error": "External data source unavailable",
                        "details": "Could not fetch data from Exchangerate API"}), 503
    rate_data = rate_resp.json()["rates"]

    # Extract data  from APIs
    for item in country_data:
        if "currencies" in item and item["currencies"]:
            country_name = item.get("name", "Unknown")
            capital = item.get("capital", "Unknown")
            region = item.get("region", "Unknown")
            popu = item.get("population", 0)
            flag = item.get("flag", "Unknown")
            currency = item["currencies"][0].get("code", None)

            # Validate entries
            # if not country_name or not popu or not currency:
            #     return jsonify({
            #         "error": "Validation failed",
            #         "details": {
            #             "name": "is required" if not country_name else None,
            #             "population": "is required" if not popu else None,
            #             "currency_code": "is required" if not currency else None
            #         }
            #     }), 400

            # Compute GDP
            if currency is None:
                exch_rate = None
                gdp = 0
            else:
                if currency in rate_data:
                    exch_rate = rate_data[currency]
                    gdp = popu * random.randint(1000, 2000) / exch_rate
                else:
                    exch_rate = None
                    gdp = None

            # Check for existing data
            existing_country = session.query(CountryData).filter(CountryData.name.ilike(country_name)).first()
            if existing_country:
                existing_country.name = country_name
                existing_country.capital = capital
                existing_country.region = region
                existing_country.population = popu
                existing_country.flag_url = flag
                existing_country.currency_code = currency
                existing_country.exchange_rate = exch_rate
                existing_country.estimated_gdp = gdp

            # OR Add New data
            else:
                new_country = CountryData(
                    name=country_name,
                    capital=capital,
                    region=region,
                    population=popu,
                    currency_code=currency,
                    flag_url=flag,
                    exchange_rate=exch_rate,
                    estimated_gdp=gdp
                )
                session.add(new_country)

            # Create or update timestamp
            existing_timestamp = session.query(Refresh).first()
            if existing_timestamp:
                existing_timestamp.last_refreshed_at = datetime.now(timezone.utc)

            else:
                refresh_time = Refresh(
                    last_refreshed_at=datetime.now(timezone.utc)
                )
                session.add(refresh_time)

    # Commit Changes and Generate Image
    session.commit()
    generate_summary_image(session)
    return jsonify({"Successful": "Done"})


@app.route("/countries")
def filter_by():
    region = request.args.get("region")
    currency = request.args.get("currency")
    gdp_sort = request.args.get("sort", "").lower() in ("true", "1", "yes")

    query = session.query(CountryData)

    if region:
        query = query.filter(func.lower(CountryData.region) == region.lower())
    if currency:
        query = query.filter(func.lower(CountryData.currency_code) == currency.lower())

    sortable_columns = {
        "name": CountryData.name,
        "population": CountryData.population,
        "gdp": CountryData.estimated_gdp,
        "region": CountryData.region,
        "currency": CountryData.currency_code,
    }

    if gdp_sort in sortable_columns:
        query = query.order_by(sortable_columns[gdp_sort].desc())
    else:
        # Default sort if no valid column provided
        query = query.order_by(CountryData.estimated_gdp.desc())

    results = query.all()

    response = [{
        "id": r.id,
        "name": r.name,
        "capital": r.capital,
        "region": r.region,
        "population": r.population,
        "currency_code": r.currency_code,
        "flag_url": r.flag_url,
        "exchange_rate": r.exchange_rate,
        "estimated_gdp": r.estimated_gdp
    } for r in results]

    return jsonify(response)


@app.route("/country/<string:name>")
def fetch_country(name):
    results = session.query(CountryData).filter(CountryData.name.ilike(name)).first()
    if not results:
        return jsonify({"error": "Country not found"}), 404
    response = {
        "id": results.id,
        "name": results.name,
        "capital": results.capital,
        "region": results.region,
        "population": results.population,
        "currency_code": results.currency_code,
        "flag_url": results.flag_url,
        "exchange_rate": results.exchange_rate,
        "estimated_gdp": results.estimated_gdp
    }

    return jsonify(response)


@app.route("/status")
def country_log():
    results = session.query(CountryData).count()
    last = session.query(Refresh).first()

    return jsonify({"Total_countries": results,
                    "last_refreshed_at": last.last_refreshed_at.isoformat()})


@app.route("/countries/image", methods=["GET"])
def get_summary_image():
    image_path = "cache/summary.png"

    if not os.path.exists(image_path):
        return jsonify({"error": "Summary image not found"}), 404

    return send_file(image_path, mimetype="image/png")


@app.route("/country/<string:name>", methods=["DELETE"])
def delete_country(name):
    result = session.query(CountryData).filter(CountryData.name.ilike(name)).first()

    if not result:
        return jsonify({"error": f"Country '{name}' not found"}), 404

    session.delete(result)
    session.commit()

    return jsonify({"message": f"Country '{name}' deleted successfully"}), 200


if __name__ == "__main__":
    port = int(environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
