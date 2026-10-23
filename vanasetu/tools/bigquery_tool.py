"""
VanaSetu BigQuery Tool
======================
Handles data warehouse queries for plantation parcels, historical satellite
indices (NDVI/NDWI/EVI), baseline metrics, and field survey archives.

Features:
- Live Google Cloud BigQuery execution when GCP credentials are available.
- Resilient local offline mock engine with realistic Indian forestry data
  (Maharashtra, Odisha, Karnataka, Madhya Pradesh, Telangana).
"""

from __future__ import annotations

import os
import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from vanasetu.models import (
    PlantationParcel,
    SpeciesRecord,
    VegetationReading,
    WorkOrder,
    WorkOrderStatus,
    UrgencyLevel,
    CauseCategory,
)

logger = logging.getLogger(__name__)

# Realistic mock Indian plantation parcels for out-of-the-box execution
DEFAULT_PARCELS: List[Dict[str, Any]] = [
    {
        "parcel_id": "MH-YTL-2024-001",
        "state": "Maharashtra",
        "district": "Yavatmal",
        "forest_division": "Yavatmal Forest Division",
        "range_name": "Pandharkawada",
        "beat_name": "Mukutban",
        "latitude": 19.9850,
        "longitude": 78.4950,
        "area_hectares": 12.5,
        "plantation_date": "2024-07-15",
        "afforestation_scheme": "CAMPA",
        "species_mix": [
            {"species_name": "Azadirachta indica", "common_name": "Neem", "count": 2500, "is_deciduous": False, "drought_tolerance": "HIGH"},
            {"species_name": "Phyllanthus emblica", "common_name": "Amla", "count": 1800, "is_deciduous": False, "drought_tolerance": "MODERATE"},
            {"species_name": "Dalbergia sissoo", "common_name": "Shisham", "count": 1200, "is_deciduous": False, "drought_tolerance": "HIGH"},
            {"species_name": "Tectona grandis", "common_name": "Teak", "count": 1000, "is_deciduous": True, "drought_tolerance": "MODERATE"}
        ],
        "soil_type": "Black Cotton",
        "irrigation_type": "Rainfed",
        "fencing_type": "Solar Electric",
        "assigned_officer": "Ramesh Rathod (Beat Guard)",
        "officer_phone": "+91-9421112345"
    },
    {
        "parcel_id": "OR-SMP-2024-003",
        "state": "Odisha",
        "district": "Mayurbhanj",
        "forest_division": "Baripada Division",
        "range_name": "Pithabata",
        "beat_name": "Similipal Buffer Beat 4",
        "latitude": 21.9320,
        "longitude": 86.4250,
        "area_hectares": 18.0,
        "plantation_date": "2024-06-25",
        "afforestation_scheme": "Green India Mission",
        "species_mix": [
            {"species_name": "Shorea robusta", "common_name": "Sal", "count": 3500, "is_deciduous": True, "drought_tolerance": "MODERATE"},
            {"species_name": "Terminalia alata", "common_name": "Asan", "count": 2500, "is_deciduous": True, "drought_tolerance": "HIGH"},
            {"species_name": "Terminalia arjuna", "common_name": "Arjun", "count": 1500, "is_deciduous": False, "drought_tolerance": "HIGH"}
        ],
        "soil_type": "Red Laterite",
        "irrigation_type": "Check Dam Trench",
        "fencing_type": "Barbed Wire",
        "assigned_officer": "Subhashree Marndi (Forester)",
        "officer_phone": "+91-9437198765"
    },
    {
        "parcel_id": "KA-WGH-2023-014",
        "state": "Karnataka",
        "district": "Chikkamagaluru",
        "forest_division": "Kudremukh Wildlife Division",
        "range_name": "Kalasa",
        "beat_name": "Shola Restoration Beat A",
        "latitude": 13.2350,
        "longitude": 75.3850,
        "area_hectares": 8.0,
        "plantation_date": "2023-08-10",
        "afforestation_scheme": "Western Ghats Eco-Restoration",
        "species_mix": [
            {"species_name": "Syzygium cumini", "common_name": "Jamun", "count": 1500, "is_deciduous": False, "drought_tolerance": "LOW"},
            {"species_name": "Cinnamomum verum", "common_name": "Dalchini / Wild Cinnamon", "count": 1000, "is_deciduous": False, "drought_tolerance": "LOW"},
            {"species_name": "Artocarpus heterophyllus", "common_name": "Halasu / Wild Jackfruit", "count": 800, "is_deciduous": False, "drought_tolerance": "MODERATE"}
        ],
        "soil_type": "Humus Rich Forest Loam",
        "irrigation_type": "Rainfed",
        "fencing_type": "Cattle Trench",
        "assigned_officer": "Naveen Kumar (Beat Forester)",
        "officer_phone": "+91-9480112233"
    },
    {
        "parcel_id": "MP-BDH-2024-007",
        "state": "Madhya Pradesh",
        "district": "Umaria",
        "forest_division": "Bandhavgarh Buffer Division",
        "range_name": "Manpur",
        "beat_name": "Dhamokhar Beat",
        "latitude": 23.7120,
        "longitude": 81.0250,
        "area_hectares": 20.0,
        "plantation_date": "2024-07-02",
        "afforestation_scheme": "CAMPA",
        "species_mix": [
            {"species_name": "Tectona grandis", "common_name": "Sagwan / Teak", "count": 5000, "is_deciduous": True, "drought_tolerance": "HIGH"},
            {"species_name": "Anogeissus latifolia", "common_name": "Dhaora", "count": 2000, "is_deciduous": True, "drought_tolerance": "HIGH"},
            {"species_name": "Madhuca longifolia", "common_name": "Mahua", "count": 800, "is_deciduous": True, "drought_tolerance": "HIGH"}
        ],
        "soil_type": "Sandy Loam",
        "irrigation_type": "Rainfed",
        "fencing_type": "Solar Electric",
        "assigned_officer": "Deepak Tiwari (Van Rakshak)",
        "officer_phone": "+91-9425887766"
    },
    {
        "parcel_id": "MH-RTG-2024-022",
        "state": "Maharashtra",
        "district": "Ratnagiri",
        "forest_division": "Ratnagiri Territorial",
        "range_name": "Chiplun",
        "beat_name": "Khed Ghat",
        "latitude": 17.5320,
        "longitude": 73.5180,
        "area_hectares": 6.5,
        "plantation_date": "2024-06-18",
        "afforestation_scheme": "Coastal Mangrove & Western Ghats Buffer",
        "species_mix": [
            {"species_name": "Mangifera indica", "common_name": "Wild Mango", "count": 1200, "is_deciduous": False, "drought_tolerance": "MODERATE"},
            {"species_name": "Garcinia indica", "common_name": "Kokum", "count": 1500, "is_deciduous": False, "drought_tolerance": "LOW"}
        ],
        "soil_type": "Lateritic Clay Loam",
        "irrigation_type": "Rainfed",
        "fencing_type": "Chain-link",
        "assigned_officer": "Sujata Sawant (Van Pal)",
        "officer_phone": "+91-9422004455"
    },
    {
        "parcel_id": "TS-ADB-2024-009",
        "state": "Telangana",
        "district": "Adilabad",
        "forest_division": "Eturnagaram Buffer",
        "range_name": "Utnoor",
        "beat_name": "Indervelli Beat",
        "latitude": 19.3750,
        "longitude": 78.7120,
        "area_hectares": 14.0,
        "plantation_date": "2024-07-20",
        "afforestation_scheme": "Telangana Ku Haritha Haram",
        "species_mix": [
            {"species_name": "Pterocarpus marsupium", "common_name": "Bijasal / Vengi", "count": 2200, "is_deciduous": True, "drought_tolerance": "HIGH"},
            {"species_name": "Azadirachta indica", "common_name": "Neem", "count": 2000, "is_deciduous": False, "drought_tolerance": "HIGH"}
        ],
        "soil_type": "Red Sandy Soil",
        "irrigation_type": "Borewell + Bowser",
        "fencing_type": "Solar Electric",
        "assigned_officer": "K. Srinivas (Forest Section Officer)",
        "officer_phone": "+91-9440119988"
    }
]


class BigQueryTool:
    """
    Client for querying parcel boundaries, telemetry time-series, and persisting work orders.
    Falls back gracefully to a fully populated local in-memory store if GCP is not configured.
    """

    def __init__(self, gcp_project: Optional[str] = None, dataset_id: str = "vanasetu_monitoring"):
        self.gcp_project = gcp_project or os.getenv("GCP_PROJECT_ID")
        self.dataset_id = dataset_id
        self.client = None
        self._mock_parcels: Dict[str, PlantationParcel] = {}
        self._mock_vegetation: Dict[str, List[VegetationReading]] = {}
        self._mock_work_orders: Dict[str, WorkOrder] = {}
        self._storage_file = os.getenv("VANASETU_STORE_PATH", ".vanasetu_work_orders.json")

        self._initialize_mock_database()
        self._load_persisted_work_orders()

        if self.gcp_project and os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            try:
                from google.cloud import bigquery
                self.client = bigquery.Client(project=self.gcp_project)
                logger.info(f"Initialized live Google Cloud BigQuery client for {self.gcp_project}")
            except Exception as e:
                logger.warning(f"Failed to initialize live BigQuery client: {e}. Defaulting to mock engine.")
                self.client = None

    def _load_persisted_work_orders(self) -> None:
        """Loads work orders from local cache if present."""
        if os.path.exists(self._storage_file):
            try:
                with open(self._storage_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data:
                        order = WorkOrder(**item)
                        self._mock_work_orders[order.work_order_id] = order
            except Exception as e:
                logger.debug(f"Could not load local work orders file: {e}")

    def _sync_persisted_work_orders(self) -> None:
        """Persists current work orders to local cache."""
        try:
            with open(self._storage_file, "w", encoding="utf-8") as f:
                json.dump([o.model_dump() for o in self._mock_work_orders.values()], f, indent=2)
        except Exception as e:
            logger.debug(f"Could not save local work orders file: {e}")

    def _initialize_mock_database(self) -> None:
        """Populates in-memory database with realistic Indian forestry sample data."""
        for p in DEFAULT_PARCELS:
            species_objs = [SpeciesRecord(**sp) for sp in p["species_mix"]]
            data = dict(p)
            data["species_mix"] = species_objs
            parcel = PlantationParcel(**data)
            self._mock_parcels[parcel.parcel_id] = parcel

            # Generate realistic 30-day baseline telemetry
            self._mock_vegetation[parcel.parcel_id] = self._create_baseline_telemetry(parcel)

    def _create_baseline_telemetry(self, parcel: PlantationParcel) -> List[VegetationReading]:
        """Creates realistic Sentinel-2 time series for the parcel."""
        readings = []
        base_ndvi = 0.68 if "WGH" in parcel.parcel_id else 0.58
        base_ndwi = 0.42 if "WGH" in parcel.parcel_id else 0.32

        now = datetime.now()
        for i in range(10, 0, -1):
            t = (now - timedelta(days=i * 5)).strftime("%Y-%m-%dT10:30:00Z")
            readings.append(
                VegetationReading(
                    parcel_id=parcel.parcel_id,
                    timestamp=t,
                    ndvi=round(base_ndvi + (i % 3) * 0.01 - 0.01, 3),
                    ndwi=round(base_ndwi + (i % 2) * 0.01 - 0.01, 3),
                    evi=round(base_ndvi * 0.85, 3),
                    cloud_cover_pct=round((i % 4) * 2.5, 1),
                    baseline_ndvi_mean=base_ndvi,
                    baseline_ndvi_std=0.04,
                    ndvi_drop_pct=0.0,
                    z_score=0.1,
                    is_anomaly=False,
                )
            )
        return readings

    def get_parcel(self, parcel_id: str) -> Optional[PlantationParcel]:
        """Retrieves parcel specification by ID."""
        if self.client:
            try:
                query = f"""
                SELECT * FROM `{self.gcp_project}.{self.dataset_id}.parcels`
                WHERE parcel_id = @parcel_id LIMIT 1
                """
                from google.cloud import bigquery
                job_config = bigquery.QueryJobConfig(
                    query_parameters=[bigquery.ScalarQueryParameter("parcel_id", "STRING", parcel_id)]
                )
                results = self.client.query(query, job_config=job_config).result()
                for row in results:
                    return PlantationParcel(**dict(row))
            except Exception as e:
                logger.warning(f"BigQuery remote query failed: {e}. Falling back to mock store.")

        return self._mock_parcels.get(parcel_id)

    def list_parcels(self) -> List[PlantationParcel]:
        """Returns list of all monitored plantation parcels."""
        if self.client:
            try:
                query = f"SELECT * FROM `{self.gcp_project}.{self.dataset_id}.parcels`"
                results = self.client.query(query).result()
                return [PlantationParcel(**dict(row)) for row in results]
            except Exception as e:
                logger.warning(f"BigQuery list failed: {e}. Using mock.")
        return list(self._mock_parcels.values())

    def get_vegetation_history(self, parcel_id: str, limit: int = 20) -> List[VegetationReading]:
        """Fetches historical Sentinel-2 vegetation index readings for the parcel."""
        if self.client:
            try:
                query = f"""
                SELECT * FROM `{self.gcp_project}.{self.dataset_id}.vegetation_telemetry`
                WHERE parcel_id = @parcel_id
                ORDER BY timestamp DESC
                LIMIT @limit
                """
                from google.cloud import bigquery
                job_config = bigquery.QueryJobConfig(
                    query_parameters=[
                        bigquery.ScalarQueryParameter("parcel_id", "STRING", parcel_id),
                        bigquery.ScalarQueryParameter("limit", "INT64", limit),
                    ]
                )
                results = self.client.query(query, job_config=job_config).result()
                return [VegetationReading(**dict(row)) for row in results]
            except Exception as e:
                logger.warning(f"BigQuery fetch telemetry failed: {e}. Using mock store.")

        return self._mock_vegetation.get(parcel_id, [])[-limit:]

    def get_latest_vegetation(self, parcel_id: str) -> Optional[VegetationReading]:
        """Gets the most recent satellite telemetry observation for parcel."""
        history = self.get_vegetation_history(parcel_id, limit=1)
        return history[-1] if history else None

    def save_vegetation_reading(self, reading: VegetationReading) -> bool:
        """Appends new satellite telemetry reading into BigQuery."""
        if parcel_id := reading.parcel_id:
            if parcel_id not in self._mock_vegetation:
                self._mock_vegetation[parcel_id] = []
            self._mock_vegetation[parcel_id].append(reading)

        if self.client:
            try:
                table_id = f"{self.gcp_project}.{self.dataset_id}.vegetation_telemetry"
                errors = self.client.insert_rows_json(table_id, [reading.model_dump()])
                if errors:
                    logger.error(f"Error inserting vegetation rows to BigQuery: {errors}")
                    return False
                return True
            except Exception as e:
                logger.warning(f"Failed to persist reading to live BigQuery: {e}")
        return True

    def save_work_order(self, work_order: WorkOrder) -> bool:
        """Saves a generated work order to BigQuery records."""
        self._mock_work_orders[work_order.work_order_id] = work_order
        self._sync_persisted_work_orders()
        if self.client:
            try:
                table_id = f"{self.gcp_project}.{self.dataset_id}.work_orders"
                errors = self.client.insert_rows_json(table_id, [work_order.model_dump()])
                if errors:
                    logger.error(f"Error saving work order to BigQuery: {errors}")
                    return False
                return True
            except Exception as e:
                logger.warning(f"Failed to save work order to live BigQuery: {e}")
        return True

    def get_work_order(self, work_order_id: str) -> Optional[WorkOrder]:
        """Retrieves a work order by ID."""
        return self._mock_work_orders.get(work_order_id)

    def list_work_orders(self, parcel_id: Optional[str] = None) -> List[WorkOrder]:
        """Lists all persisted work orders, optionally filtered by parcel."""
        orders = list(self._mock_work_orders.values())
        if parcel_id:
            orders = [o for o in orders if o.parcel_id == parcel_id]
        return orders
