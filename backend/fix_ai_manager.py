import json

with open('c:/Users/lenovo/Desktop/DGUpdatedProject (2)/DGUpdatedProject/backend/ai_manager.py', 'r') as f:
    lines = f.readlines()

cut_idx = -1
for i, line in enumerate(lines):
    if line.startswith('def get_strategic_actions'):
        cut_idx = i
        break

good_lines = lines[:cut_idx]

tail = """def get_strategic_actions(metrics_summary, sample_rows):
    global API_KEY_VALID
    fallbacks = [
        {"title": "Implement Automation", "priority": "High", "icon": "fa-bolt", "context": "Current manual processes create bottlenecks.", "steps": ["Identify redundant tasks", "Deploy software tools", "Train team"]},
        {"title": "Expand Market Reach", "priority": "Medium", "icon": "fa-globe", "context": "New demographics remain untapped.", "steps": ["Conduct market research", "Tailor ad campaigns", "Launch pilot program"]}
    ]
    if not client or not API_KEY_VALID:
        return fallbacks

    try:
        payload = {"metrics": metrics_summary, "sample_data": sample_rows}
        print("REQUESTING STRATEGIC ACTIONS from Gemini...")
        response = call_gemini_with_retry(lambda: client.models.generate_content(
            model="gemini-2.5-flash-lite",
            config=types.GenerateContentConfig(
                system_instruction=STRATEGIC_ACTION_PROMPT,
                response_mime_type="application/json"
            ),
            contents=[f"Generate 3-4 strategic B2B action cards based on this dataset context: {json.dumps(payload)}"]
        ))
        
        if response.text:
            cleaned = clean_ai_json(response.text)
            actions = json.loads(cleaned)
            if isinstance(actions, list) and len(actions) >= 2:
                print(f"SUCCESS: AI successfully synthesized {len(actions)} strategic action cards!")
                return actions
        return fallbacks
    except Exception as e:
        print(f"AI STRATEGIC ACTIONS ERROR: {e}")
        return fallbacks

MASTER_INTELLIGENCE_PROMPT = \"\"\"# Advanced AI Business Intelligence Engine

## Objective
You are an **Expert Business Intelligence Architect and Senior Data Consultant**.
Your goal is to generate the ENTIRE dashboard intelligence in one single highly-structured JSON response based on the dataset schema, top raw metrics, and sample rows provided.

## Guidelines

### 1. KPIs (Key Performance Indicators)
Translate the raw numerical metrics into strategic business labels. 
- Example: A metric named "Total_Revenue" should have an impact_label of "Total Gross Revenue" and an insight explaining why it matters.

### 2. Semantic Charts & Visualizations
Design between 15 to 20 visually and structurally diverse charts.
- **QUALITY CONTROL: NO BORING FLAT CHARTS**
  1. NEVER plot a continuous flat variable against Time/Dates (e.g., plotting "Fuel Price" or "CPI" over Time).
  2. ALWAYS prefer AGGREGATION: Group a continuous variable by a categorical bucket (e.g., "Total Sales by Region", "Average Salary by Department").
  3. Only use Line charts for highly volatile metrics with significant variance over time.
- Uses allowed types: `line`, `bar`, `doughnut`, `pie`, `polarArea`, `bar` (with style="horizontal"), `matrix` (Heatmap), `grouped_bar`, `dual_axis`.
- **Advanced Types Rules**:
  - `matrix`: Requires `x_column`, `y_column`, and `z_column` (for heat value).
  - `grouped_bar`: Requires `x_column`, `y_column`, and `group_column`.
  - `dual_axis`: Requires `x_column`, `y1_column` (bar), and `y2_column` (line).
- **strategic_description**: For EACH chart, you MUST provide an array of exactly 5 string bullet points (without the bullet character itself). These points must analyze the specific trend, insight, impact, risk, and strategic action based on the chart configuration.

### 3. Strategic Action Planner
Synthesize 3 executive-level Action Cards (High, Medium, and Low Priority) based on the overall data.
- Each action card must have a specific `title`, `priority` (High/Medium/Low), an `icon` (font-awesome class like "fa-chart-line"), a brief `context`, and an array of 3-5 concrete `steps`.

## Output Validation
You MUST output strictly a valid JSON object matching this exact structure:
{
  "kpis": [
    {
      "original_name": "metric_name",
      "impact_label": "Strategic Grounded Label",
      "insight": "Clear executive insight (15-20 words)."
    }
  ],
  "charts": [
    {
      "title": "Professional Chart Title",
      "type": "pie",
      "style": "standard",
      "x_column": "exact_x_col_name",
      "y_column": "exact_y_col_name",
      "z_column": "optional_for_matrix",
      "group_column": "optional_for_grouped_bar",
      "y1_column": "optional_for_dual_axis",
      "y2_column": "optional_for_dual_axis",
      "aggregation": "sum",
      "strategic_description": [
         "Point 1", "Point 2", "Point 3", "Point 4", "Point 5"
      ]
    }
  ],
  "actions": [
    {
      "title": "Action Title",
      "priority": "High",
      "icon": "fa-bullseye",
      "context": "Brief context for the action.",
      "steps": ["Step 1", "Step 2", "Step 3"]
    }
  ]
}
\"\"\"

def generate_master_intelligence(metrics_data, columns_metadata, sample_rows):
    \"\"\"
    Connects to Gemini to generate KPIs, Charts, Descriptions, and Actions in ONE single API call.
    \"\"\"
    global API_KEY_VALID
    if not client or not API_KEY_VALID:
        print("MASTER INTELLIGENCE SKIPPED: Client or Key Invalid")
        return {"kpis": [], "charts": [], "actions": []}

    try:
        payload = {
            "metrics_to_analyze": metrics_data,
            "columns": columns_metadata,
            "sample_data": sample_rows[:5]
        }
        
        import json
        print("REQUESTING MASTER INTELLIGENCE FROM GEMINI (Mega-Prompt)...")
        response = call_gemini_with_retry(lambda: client.models.generate_content(
            model="gemini-2.5-flash-lite",
            config=types.GenerateContentConfig(
                system_instruction=MASTER_INTELLIGENCE_PROMPT,
                response_mime_type="application/json"
            ),
            contents=[f"Analyze this dataset context and generate the master JSON intelligence object: {json.dumps(payload)}"]
        ))
        
        if response.text:
            cleaned = clean_ai_json(response.text)
            master_data = json.loads(cleaned)
            print("SUCCESS: Master Intelligence generated successfully!")
            
            # Ensure safe fallback keys
            if "kpis" not in master_data: master_data["kpis"] = []
            if "charts" not in master_data: master_data["charts"] = []
            if "actions" not in master_data: master_data["actions"] = []
            
            return master_data
            
        return {"kpis": [], "charts": [], "actions": []}
    except Exception as e:
        print(f"MASTER INTELLIGENCE ERROR: {e}")
        return {"kpis": [], "charts": [], "actions": []}
"""

with open('c:/Users/lenovo/Desktop/DGUpdatedProject (2)/DGUpdatedProject/backend/ai_manager.py', 'w') as f:
    f.writelines(good_lines)
    f.write(tail)
