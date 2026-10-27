from flask import Blueprint, render_template
from flask_login import login_required
from app.models import GroundStation

stations_bp = Blueprint("stations", __name__)

@stations_bp.route("/stations")
@login_required
def list_stations():
    stations = GroundStation.query.order_by(GroundStation.name).all()
    return render_template("stations.html", stations=stations)

