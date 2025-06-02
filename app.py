from flask import Flask, render_template, request, session, make_response
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os
from datetime import datetime
from fpdf import FPDF

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Required for sessions
os.makedirs("static", exist_ok=True)

# ----- Simulation Constants -----
SEGMENTS = ["Traditional", "Low End", "High End", "Performance", "Size"]
MAX_ROUNDS = 20

def init_state():
    return {
        "current_round": 1,
        "selected_segment": "Traditional",
        "segments": {
            seg: {
                # R&D Department
                "rd": {
                    "performance": 5.0,
                    "size": 15.0,
                    "mtbf": 17000,
                    "automation": 3.0,
                    "capacity": 2.0
                },
                # Marketing Department
                "marketing": {
                    "price": 25.00,
                    "promotion": 1.5,  # in millions
                    "sales": 2.0  # in millions
                },
                # Production Department
                "production": {
                    "schedule": 2.0  # in millions
                },
                # Finance Department
                "finance": {
                    "current_debt": 0.0,
                    "long_term_debt": 0.0,
                    "stock_issued": 0.0
                }
            } for seg in SEGMENTS
        },
        # Global Financials
        "financials": {
            "cash": 50.0,  # in millions
            "accounts_receivable": 30,
            "accounts_payable": 30
        },
        "decision_history": [],
        "reset_count": 0        
    }

# Static information from document
info = {
    "buying_criteria": {
        "Traditional": {
            "Age": {"importance": "47%", "ideal": "2 years"},
            "Price": {"importance": "23%", "range": "$20.00-$30.00"},
            "Positioning": {"importance": "21%", "ideal": "Size 16.0/Performance 4.0"},
            "MTBF": {"importance": "9%", "range": "14,000-19,000 hrs"}
        },
        "Low End": {
            "Price": {"importance": "35%", "range": "$15.00-$25.00"},
            "Age": {"importance": "30%", "ideal": "3 years"},
            "Positioning": {"importance": "25%", "ideal": "Size 17.0/Performance 3.0"},
            "MTBF": {"importance": "10%", "range": "12,000-17,000 hrs"}
        },
        "High End": {
            "Positioning": {"importance": "40%", "ideal": "Size 11.1/Performance 8.9"},
            "Age": {"importance": "29%", "ideal": "0 years"},
            "MTBF": {"importance": "19%", "range": "20,000-25,000 hrs"},
            "Price": {"importance": "12%", "range": "$30.00-$40.00"}
        },
        "Performance": {
            "Positioning": {"importance": "45%", "ideal": "Size 14.0/Performance 10.0"},
            "MTBF": {"importance": "25%", "range": "22,000-27,000 hrs"},
            "Price": {"importance": "20%", "range": "$35.00-$45.00"},
            "Age": {"importance": "10%", "ideal": "1 year"}
        },
        "Size": {
            "Positioning": {"importance": "50%", "ideal": "Size 9.0/Performance 6.0"},
            "Price": {"importance": "25%", "range": "$25.00-$35.00"},
            "MTBF": {"importance": "15%", "range": "18,000-23,000 hrs"},
            "Age": {"importance": "10%", "ideal": "2 years"}
        }
    },
    "scorecard_weights": {
        "Financial": 40,
        "Customer": 25,
        "Internal Business Process": 20,
        "Learning & Growth": 15
    }
}

def calculate_positioning_map(sim_data):
    plt.figure(figsize=(12, 10))
    plt.title(f"Perceptual Map - Round {sim_data['current_round']}")
    plt.xlabel("Performance (0-20)")
    plt.ylabel("Size (0-20)")
    plt.xlim(0, 20)
    plt.ylim(20, 0)  # Inverted axis
    
    # Plot segment regions
    segment_colors = {
        "Traditional": "blue",
        "Low End": "green",
        "High End": "red",
        "Performance": "purple",
        "Size": "orange"
    }
    
    # Plot ideal spots and product positions
    for seg in SEGMENTS:
        # Plot segment ideal spot
        plt.scatter(
            sim_data["segments"][seg]["rd"]["performance"],
            sim_data["segments"][seg]["rd"]["size"],
            s=500,
            marker='o',
            facecolors='none',
            edgecolors=segment_colors[seg],
            label=f"{seg} Segment"
        )
        
        # Plot actual product position
        plt.scatter(
            sim_data["segments"][seg]["rd"]["performance"],
            sim_data["segments"][seg]["rd"]["size"],
            s=100,
            color=segment_colors[seg],
            marker='x'
        )
    
    plt.legend(loc='upper right')
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("static/positioning.png")
    plt.close()

@app.route("/", methods=["GET", "POST"])
def index():
    if "sim_data" not in session:
        session["sim_data"] = init_state()
    
    sim_data = session["sim_data"]
    
    if request.method == "POST":
        if "select_segment" in request.form:
            sim_data["selected_segment"] = request.form["segment"]
        elif "update_decisions" in request.form:
            current_seg = sim_data["selected_segment"]
            
            # Update all parameters
            fields = [
                'performance', 'size', 'price', 'promotion', 'sales',
                'production', 'capacity', 'current_debt', 'long_term_debt', 'stock_issued'
            ]
            updates = {field: request.form.get(field) for field in fields}
            
            # Apply updates
            sim_data["segments"][current_seg]["rd"].update({
                "performance": float(updates["performance"]),
                "size": float(updates["size"]),
                "capacity": float(updates["capacity"])
            })
            
            sim_data["segments"][current_seg]["marketing"].update({
                "price": float(updates["price"]),
                "promotion": float(updates["promotion"]),
                "sales": float(updates["sales"])
            })
            
            sim_data["segments"][current_seg]["production"]["schedule"] = float(updates["production"])
            
            sim_data["segments"][current_seg]["finance"].update({
                "current_debt": float(updates["current_debt"]),
                "long_term_debt": float(updates["long_term_debt"]),
                "stock_issued": float(updates["stock_issued"])
            })
            
            # Add to history
            history_entry = {
                "round": sim_data["current_round"],
                "segment": current_seg,
                "decisions": updates,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            sim_data["decision_history"].append(history_entry)
            
            if sim_data["current_round"] < MAX_ROUNDS:
                sim_data["current_round"] += 1
            
        session["sim_data"] = sim_data
    
    calculate_positioning_map(sim_data)
    
    return render_template(
        "index.html",
        sim_data=sim_data,
        segments=SEGMENTS,
        info=info,
        max_rounds=MAX_ROUNDS
    )

@app.route("/reset", methods=["POST"])
def reset_simulation():
    sim_data = session["sim_data"]
    current_seg = sim_data["selected_segment"]
    initial_state = init_state()["segments"][current_seg]
    sim_data["segments"][current_seg] = initial_state
    sim_data["reset_count"] += 1
    session["sim_data"] = sim_data
    return "OK", 200

@app.route("/export/<report_type>")
def export_report(report_type):
    sim_data = session["sim_data"]
    
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # Add title
    pdf.cell(200, 10, txt=f"{report_type.capitalize()} Report - Round {sim_data['current_round']}", ln=1, align='C')
    
    # Add content
    if report_type == "balance":
        pdf.cell(200, 10, txt=f"Cash: ${sim_data['financials']['cash']}M", ln=1)
        pdf.cell(200, 10, txt=f"Accounts Receivable: {sim_data['financials']['accounts_receivable']} days", ln=1)
        pdf.cell(200, 10, txt=f"Accounts Payable: {sim_data['financials']['accounts_payable']} days", ln=1)
    elif report_type == "cashflow":
        pdf.cell(200, 10, txt=f"Current Debt: ${sim_data['segments'][sim_data['selected_segment']]['finance']['current_debt']}M", ln=1)
        pdf.cell(200, 10, txt=f"Long Term Debt: ${sim_data['segments'][sim_data['selected_segment']]['finance']['long_term_debt']}M", ln=1)
        pdf.cell(200, 10, txt=f"Stock Issued: ${sim_data['segments'][sim_data['selected_segment']]['finance']['stock_issued']}M", ln=1)
    elif report_type == "income":
        production_cost = sim_data['segments'][sim_data['selected_segment']]['production']['schedule'] * 2
        marketing_cost = sim_data['segments'][sim_data['selected_segment']]['marketing']['promotion'] + \
                        sim_data['segments'][sim_data['selected_segment']]['marketing']['sales']
        net_profit = sim_data['financials']['cash'] - production_cost - marketing_cost
        pdf.cell(200, 10, txt=f"Production Cost: ${production_cost}M", ln=1)
        pdf.cell(200, 10, txt=f"Marketing Cost: ${marketing_cost}M", ln=1)
        pdf.cell(200, 10, txt=f"Net Profit: ${net_profit}M", ln=1)
    
    response = make_response(pdf.output(dest='S').encode('latin-1'))
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename={report_type}_report.pdf'
    return response

if __name__ == "__main__":
    app.run(debug=True)