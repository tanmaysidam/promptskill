"""
VanaSetu Work Order Tool
========================
Generates, formats, and persists field intervention work orders.
Includes bilingual instructions (English and Hindi) tailored for Indian
Forest Department beat staff and Vana Samiti (JFMC) community crews.
"""

from __future__ import annotations

import uuid
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from vanasetu.models import (
    WorkOrder,
    WorkOrderStatus,
    UrgencyLevel,
    CauseCategory,
    VerificationResult,
    PlantationParcel,
    DiagnosisResult,
)

logger = logging.getLogger(__name__)

# Template mapping for field actions, equipment, and bilingual instructions
ACTION_TEMPLATES: Dict[CauseCategory, Dict[str, Any]] = {
    CauseCategory.DROUGHT_STRESS: {
        "en": (
            "EMERGENCY IRRIGATION & SOIL CONSERVATION: Deploy tractor bowser/tanker to deliver "
            "10-15 Litres per sapling. Apply thick organic mulch (paddy straw / dried grass) around root collar "
            "to minimize evaporative loss. Excavate shallow saucer basins around stems."
        ),
        "hi": (
            "आपातकालीन सिंचाई एवं नमी संरक्षण: प्रति पौधे 10-15 लीटर पानी टैंकर द्वारा तुरंत प्रदान करें। "
            "वाष्पीकरण रोकने हेतु पौधों की जड़ के चारों ओर पराली/सूखी घास की मल्चिंग (Mulching) बिछाएं तथा "
            "उचित थाला (Saucer basin) बनाएं।"
        ),
        "equipment": ["Tractor Water Bowser (5000L)", "Mulching Straw / Paddy Husk", "Shovels / Phawra", "Hose Pipes"],
        "base_person_days_per_ha": 3,
        "base_cost_inr_per_ha": 3500.0,
    },
    CauseCategory.SURFACE_FIRE_SCORCH: {
        "en": (
            "FIRE SUPPRESSION & BUFFER PERIMETER CLEARANCE: Clear a 5-meter wide fire break line "
            "around the affected parcel boundary. Clear dry leaf litter. Douse smoldering logs and "
            "assess root collar scorch on surviving saplings. Prune burnt branch tips."
        ),
        "hi": (
            "अग्नि शमन एवं फायर लाइन निर्माण: पौधरोपण सीमा पर 5 मीटर चौड़ी फायर लाइन (Fire break) तुरंत "
            "साफ करें। सूखी पत्तियों और सुलगती लकड़ियों को बुझाएं। झुलसे हुए पौधों की छंटाई करें तथा जड़ को सुरक्षित करें।"
        ),
        "equipment": ["Backpack Water Mist Fire Extinguishers", "Fire Rakes / Bilhook", "Hand Sprayers", "Safety Helmets"],
        "base_person_days_per_ha": 4,
        "base_cost_inr_per_ha": 4000.0,
    },
    CauseCategory.INVASIVE_WEED_CHOKING: {
        "en": (
            "INVASIVE WEED REMOVAL & SAPLING RELEASE: Uproot invasive Lantana camara / weeds "
            "within a 1.5m radius of each sapling. Ensure root stock is grubbed out to prevent coppicing. "
            "Stake vulnerable saplings upright."
        ),
        "hi": (
            "खरपतवार नियंत्रण (लंताना उन्मूलन): प्रत्येक पौधे के चारों तरफ 1.5 मीटर दायरे में लंताना एवं हानिकारक "
            "घास को जड़ सहित उखाड़ें ताकि पौधों को सूर्य का प्रकाश मिल सके। कमजोर पौधों को बांस का सहारा दें।"
        ),
        "equipment": ["Lantana Weed Pullers / Kassi", "Sickles / Daranti", "Bamboo Stakes", "Jute Twine"],
        "base_person_days_per_ha": 5,
        "base_cost_inr_per_ha": 4500.0,
    },
    CauseCategory.GRAZING_DAMAGE: {
        "en": (
            "PERIMETER FENCE REPAIR & CATTLE EXCLUSION: Inspect and repair breached solar electric fence wire "
            "or barbed wire. Restore broken support poles. Deepen cattle-proof trenches along vulnerable boundary. "
            "Notify village Joint Forest Management Committee."
        ),
        "hi": (
            "बाड़ मरम्मत एवं मवेशी रोकथाम: टूटी हुई सोलर इलेक्ट्रिक बाड़ अथवा कंटीले तार की तुरंत मरम्मत करें। "
            "खंभों को सीधा करें एवं कैटल-प्रूफ ट्रेंच (खाई) को गहरा करें। ग्राम वन समिति को सूचित कर मवेशी चराई रोकें।"
        ),
        "equipment": ["High-Tensile Wire Spools", "Solar Energizer Tester", "Wooden / Concrete Fence Posts", "Digging Crowbars"],
        "base_person_days_per_ha": 2,
        "base_cost_inr_per_ha": 2500.0,
    },
    CauseCategory.PEST_OUTBREAK: {
        "en": (
            "BIO-PESTICIDE SPRAY & PRUNING: Apply 5% Neem Seed Kernel Extract (NSKE) or bio-fungicide spray. "
            "Prune and safely burn heavily infested diseased foliage to stop transmission."
        ),
        "hi": (
            "जैविक कीटनाशक छिड़काव: 5% नीम तेल (NSKE) अथवा जैविक कीटनाशक का छिड़काव करें। "
            "रोगग्रस्त पत्तियों एवं शाखाओं को काटकर सुरक्षित स्थान पर नष्ट करें।"
        ),
        "equipment": ["Knapsack Battery Sprayers", "Neem Bio-pesticide (NSKE 10,000 ppm)", "Secateurs", "Protective Masks"],
        "base_person_days_per_ha": 2,
        "base_cost_inr_per_ha": 2200.0,
    },
    CauseCategory.PHENOLOGICAL_SHEDDING: {
        "en": (
            "MONITOR ONLY - NORMAL DECIDUOUS PHENOLOGY: Stand is predominantly deciduous (Teak/Sal/Dhaora) "
            "shedding leaves seasonally. Maintain normal fire-patrolling schedule; NO emergency irrigation required."
        ),
        "hi": (
            "निगरानी रखें - सामान्य पतझड़: यह सागौन/साल का प्राकृतिक पतझड़ है। आपातकालीन सिंचाई की आवश्यकता नहीं है। "
            "अग्निशमन गश्त जारी रखें।"
        ),
        "equipment": ["Monitoring Logsheet"],
        "base_person_days_per_ha": 0,
        "base_cost_inr_per_ha": 0.0,
    },
    CauseCategory.SENSOR_ARTIFACT_FALSE_ALARM: {
        "en": (
            "SENSOR ARTIFACT / CLOUD SHADOW: Vegetation drop is due to atmospheric cloud interference or shadow. "
            "Wait for next clear-sky Sentinel-2 pass; no ground intervention required."
        ),
        "hi": (
            "उपग्रह छवि बादल अवरोध: यह गिरावट बादलों की छाया के कारण उपग्रह द्वारा दर्ज की गई है। जमीनी कार्रवाई की आवश्यकता नहीं है।"
        ),
        "equipment": [],
        "base_person_days_per_ha": 0,
        "base_cost_inr_per_ha": 0.0,
    },
    CauseCategory.UNKNOWN: {
        "en": "CONDUCT DETAILED GROUND INSPECTION: Inspect site to determine cause of anomalous decline.",
        "hi": "विस्तृत जमीनी निरीक्षण करें।",
        "equipment": ["Inspection Kit"],
        "base_person_days_per_ha": 1,
        "base_cost_inr_per_ha": 800.0,
    },
}


class WorkOrderTool:
    """Tool for drafting and generating structured work orders."""

    @staticmethod
    def create_work_order(
        parcel: PlantationParcel,
        diagnosis: DiagnosisResult,
        verification: VerificationResult,
    ) -> WorkOrder:
        """
        Creates a formalized, verified work order with resource estimations
        and bilingual instructions for field dispatch.
        """
        # If verification overrode the cause (e.g. detected false alarm or phenology), use the override
        effective_cause = verification.overridden_cause or diagnosis.primary_cause

        template = ACTION_TEMPLATES.get(effective_cause, ACTION_TEMPLATES[CauseCategory.UNKNOWN])

        # Calculate estimated cost and person days
        area = parcel.area_hectares
        person_days = max(1, int(area * template["base_person_days_per_ha"]))
        estimated_cost = round(area * template["base_cost_inr_per_ha"], 2)

        # Emergency bowser or heavy expense adjustment
        if effective_cause == CauseCategory.DROUGHT_STRESS:
            estimated_cost += 5000.0  # Bowser rental surcharge

        # Check if DFO approval is required (cost > ₹15,000 INR or flag by verifier)
        dfo_approval = verification.dfo_approval_required or estimated_cost > 15000.0

        status = WorkOrderStatus.VERIFIED if verification.is_valid else WorkOrderStatus.REJECTED_BY_POLICY

        wo_id = f"WO-{parcel.state[:2].upper()}-{parcel.parcel_id[-4:]}-{uuid.uuid4().hex[:6].upper()}"
        now_str = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

        # Dispatch payload for SMS / WhatsApp API
        dispatch_payload = {
            "recipient_name": parcel.assigned_officer,
            "recipient_phone": parcel.officer_phone,
            "division": parcel.forest_division,
            "range": parcel.range_name,
            "beat": parcel.beat_name,
            "parcel_id": parcel.parcel_id,
            "urgency": diagnosis.urgency.value,
            "cause": effective_cause.value,
            "summary_hi": template["hi"][:160],  # SMS length limit
            "summary_en": template["en"][:160],
        }

        return WorkOrder(
            work_order_id=wo_id,
            parcel_id=parcel.parcel_id,
            created_at=now_str,
            status=status,
            urgency=diagnosis.urgency,
            diagnosed_cause=effective_cause,
            confidence_score=diagnosis.confidence_score,
            verification=verification,
            crew_instructions_en=template["en"],
            crew_instructions_hi=template["hi"],
            recommended_actions=diagnosis.proposed_actions or [template["en"]],
            required_equipment=template["equipment"],
            estimated_person_days=person_days,
            estimated_cost_inr=estimated_cost,
            dfo_approval_required=dfo_approval,
            assigned_beat_guard=parcel.assigned_officer,
            contact_phone=parcel.officer_phone,
            dispatch_payload=dispatch_payload,
        )
