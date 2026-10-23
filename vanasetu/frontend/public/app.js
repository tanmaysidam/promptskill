const SITES = [
  { id: "MH-YTL-2024-001", state: "Maharashtra", division: "Yavatmal Division", area: "12.5 ha", species: "Neem, Amla, Shisham, Teak", status: "DROUGHT_STRESS", badge: "badge-critical" },
  { id: "OR-SMP-2024-003", state: "Odisha", division: "Baripada Division", area: "18.0 ha", species: "Sal, Asan, Arjun", status: "FIRE_ENCROACHMENT", badge: "badge-critical" },
  { id: "KA-WGH-2023-014", state: "Karnataka", division: "Kudremukh Division", area: "8.0 ha", species: "Jamun, Dalchini, Wild Jackfruit", status: "WEED_CHOKING", badge: "badge-warning" },
  { id: "TS-ADB-2024-009", state: "Telangana", division: "Eturnagaram Buffer", area: "14.0 ha", species: "Bijasal, Neem", status: "GRAZING_DAMAGE", badge: "badge-warning" },
  { id: "MP-BDH-2024-007", state: "Madhya Pradesh", division: "Bandhavgarh Buffer", area: "20.0 ha", species: "Teak, Dhaora, Mahua", status: "SEASONAL_SHEDDING", badge: "badge-normal" },
  { id: "MH-RTG-2024-022", state: "Maharashtra", division: "Ratnagiri Territorial", area: "6.5 ha", species: "Wild Mango, Kokum", status: "NORMAL_HEALTH", badge: "badge-normal" }
];

const ORDERS = [
  {
    id: "WO-OD-003-8EBA83",
    site: "OR-SMP-2024-003 (Odisha)",
    cause: "SURFACE_FIRE_SCORCH",
    urgency: "CRITICAL",
    badge: "badge-critical",
    officer: "Subhashree Marndi (Forester)",
    cost: "₹72,000",
    dfo: true,
    hi: "अग्नि शमन एवं फायर लाइन निर्माण: पौधरोपण सीमा पर 5 मीटर चौड़ी फायर लाइन तुरंत साफ करें। सूखी पत्तियों और सुलगती लकड़ियों को बुझाएं।",
    en: "Clear a 5-meter wide fire break line around the affected parcel boundary. Clear dry leaf litter. Douse smoldering logs."
  },
  {
    id: "WO-MA-001-ACE846",
    site: "MH-YTL-2024-001 (Maharashtra)",
    cause: "DROUGHT_STRESS",
    urgency: "CRITICAL",
    badge: "badge-critical",
    officer: "Ramesh Rathod (Beat Guard)",
    cost: "₹48,750",
    dfo: true,
    hi: "आपातकालीन सिंचाई एवं नमी संरक्षण: प्रति पौधे 10-15 लीटर पानी टैंकर द्वारा तुरंत प्रदान करें। पौधों की जड़ के चारों ओर पराली/घास की मल्चिंग बिछाएं।",
    en: "Deploy tractor bowser to deliver 10-15L per sapling. Apply thick organic mulch around root collar."
  },
  {
    id: "WO-KA-014-4E03F9",
    site: "KA-WGH-2023-014 (Karnataka)",
    cause: "INVASIVE_WEED_CHOKING",
    urgency: "HIGH",
    badge: "badge-warning",
    officer: "Naveen Kumar (Beat Forester)",
    cost: "₹36,000",
    dfo: true,
    hi: "खरपतवार नियंत्रण (लंताना उन्मूलन): प्रत्येक पौधे के चारों तरफ 1.5 मीटर दायरे में लंताना एवं हानिकारक घास को जड़ सहित उखाड़ें।",
    en: "Uproot invasive Lantana camara within a 1.5m radius of each native sapling. Stake suppressed saplings upright."
  }
];

function renderDashboard() {
  const tbody = document.getElementById("parcels-tbody");
  tbody.innerHTML = SITES.map(s => `
    <tr>
      <td><strong>${s.id}</strong></td>
      <td>${s.state} <br/><small style="color:#94a3b8">${s.division}</small></td>
      <td>${s.area}</td>
      <td><small>${s.species}</small></td>
      <td><span class="badge ${s.badge}">${s.status}</span></td>
    </tr>
  `).join("");

  const ordersContainer = document.getElementById("orders-container");
  ordersContainer.innerHTML = ORDERS.map(o => `
    <div class="order-card">
      <div class="order-card-header">
        <span class="order-id">${o.id}</span>
        <span class="badge ${o.badge}">${o.urgency}</span>
      </div>
      <div><strong>${o.site}</strong> &bull; ${o.cause}</div>
      <div class="hindi-text">${o.hi}</div>
      <div class="order-meta">
        <span>Officer: ${o.officer}</span>
        <span>Cost: <strong>${o.cost}</strong> ${o.dfo ? '<span class="dfo-flag">(DFO Gate)</span>' : ''}</span>
      </div>
    </div>
  `).join("");
}

document.addEventListener("DOMContentLoaded", renderDashboard);
