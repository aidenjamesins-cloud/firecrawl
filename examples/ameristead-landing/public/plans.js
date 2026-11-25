// Generated from examples/ameristead-campaign/data/plans.json (Ameristead rate flyer + 2026 Cigna SBCs).
// Do not edit by hand; tests/plans.test.mjs checks the two stay identical.
window.PLAN_DATA = {
  "_source": "Ameristead Health rate flyer (Cigna PPO network, Marpai) and Cigna Summary of Benefits and Coverage PDFs, coverage period 01/01/2026-12/31/2026. In-network figures. Flyer disclaimer: summary snapshot, subject to change; Schedule of Benefits governs.",
  "network": "Cigna PPO",
  "common": {
    "preventive_care": "$0",
    "teledoctor": "$0",
    "specialist_referral": "No referral needed to see a specialist (per each plan's SBC)",
    "rx_specialty": "PBM management required",
    "glp1_note": "GLP-1s (e.g. Ozempic, Mounjaro): preauthorization every 6 months, A1C of 6 or more, mail order only"
  },
  "plans": [
    {
      "name": "HSA 9000",
      "hsa": true,
      "deductible": "$9,000/$18,000",
      "coinsurance": "70/30",
      "max_oop": "$10,100/$20,200",
      "primary_care": "30% after deductible",
      "specialist": "30% after deductible",
      "urgent_care": "30% after deductible",
      "rx": "30% after deductible",
      "premiums": {
        "employee": 426,
        "employee_spouse": 589,
        "employee_children": 549,
        "family": 789
      }
    },
    {
      "name": "Bronze",
      "hsa": false,
      "deductible": "$8,000/$16,000",
      "coinsurance": "70/30",
      "max_oop": "$8,700/$17,400",
      "primary_care": "$50",
      "specialist": "$120",
      "urgent_care": "$100",
      "rx": "$0/$35/$75",
      "premiums": {
        "employee": 544,
        "employee_spouse": 856,
        "employee_children": 753,
        "family": 1134
      }
    },
    {
      "name": "HSA 6000",
      "hsa": true,
      "deductible": "$6,000/$12,000",
      "coinsurance": "70/30",
      "max_oop": "$7,000/$14,000",
      "primary_care": "30% after deductible",
      "specialist": "30% after deductible",
      "urgent_care": "30% after deductible",
      "rx": "30% after deductible",
      "premiums": {
        "employee": 640,
        "employee_spouse": 1012,
        "employee_children": 889,
        "family": 1340
      }
    },
    {
      "name": "Silver",
      "hsa": false,
      "deductible": "$5,000/$10,000",
      "coinsurance": "70/30",
      "max_oop": "$8,700/$17,400",
      "primary_care": "$40",
      "specialist": "$80",
      "urgent_care": "$60",
      "rx": "$0/$35/$75",
      "premiums": {
        "employee": 674,
        "employee_spouse": 1067,
        "employee_children": 945,
        "family": 1413
      }
    },
    {
      "name": "Gold",
      "hsa": false,
      "deductible": "$3,000/$6,000",
      "coinsurance": "80/20",
      "max_oop": "$8,700/$17,400",
      "primary_care": "$35",
      "specialist": "$55",
      "urgent_care": "$55",
      "rx": "$0/$35/$75",
      "premiums": {
        "employee": 941,
        "employee_spouse": 1493,
        "employee_children": 1309,
        "family": 1981
      }
    },
    {
      "name": "Platinum",
      "hsa": false,
      "deductible": "$250/$500",
      "coinsurance": "80/20",
      "max_oop": "$1,250/$2,500",
      "primary_care": "$25",
      "specialist": "$45",
      "urgent_care": "$45",
      "rx": "$0/$35/$75",
      "premiums": {
        "employee": 1003,
        "employee_spouse": 1632,
        "employee_children": 1563,
        "family": 2993
      }
    },
    {
      "name": "Diamond",
      "hsa": false,
      "deductible": "$0/$0",
      "coinsurance": "70/30",
      "max_oop": "$6,000/$12,000",
      "primary_care": "$25",
      "specialist": "$50",
      "urgent_care": "$50",
      "rx": "$0/$35/$75",
      "premiums": {
        "employee": 873,
        "employee_spouse": 1372,
        "employee_children": 1243,
        "family": 1687
      }
    }
  ]
};
