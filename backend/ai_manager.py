import os
from google import genai
from google.genai import types
from dotenv import load_dotenv
import traceback
import json
import time

# Load API Keys
load_dotenv()
api_keys = []

# Try comma-separated first
api_keys_str = os.getenv("GEMINI_API_KEYS") or os.getenv("GEMINI_API_KEY")
if api_keys_str and api_keys_str != "PASTE_YOUR_KEY_HERE":
    api_keys.extend([k.strip() for k in api_keys_str.split(",") if k.strip()])

# Load individual separate keys (GEMINI_API_KEY_1, GEMINI_API_KEY_2, etc.)
for i in range(1, 10):
    val = os.getenv(f"GEMINI_API_KEY_{i}")
    if val and val.strip() and val.strip() not in api_keys:
        api_keys.append(val.strip())

current_key_index = 0

# Status Flag
API_KEY_VALID = True

# Initialize Client
client = None
if api_keys:
    try:
        client = genai.Client(api_key=api_keys[current_key_index])
    except Exception as e:
        print(f"CLIENT INIT ERROR: {e}")
        client = None

def switch_api_key():
    global current_key_index, client, api_keys
    if not api_keys or len(api_keys) <= 1:
        return False
    
    current_key_index = (current_key_index + 1) % len(api_keys)
    print(f"Rate limit hit! Switching to fallback API Key {current_key_index + 1} of {len(api_keys)}...")
    try:
        client = genai.Client(api_key=api_keys[current_key_index])
        return True
    except Exception as e:
        print(f"Error switching client: {e}")
        return False

EXPERT_PROMPT = """You are an Executive Business Intelligence Consultant and Senior Data Strategist.
Your task is to analyze raw numerical sums/metrics of an uploaded dataset and provide highly descriptive, professional, and business-relevant corporate KPI labels and executive insights.

GUIDELINES:
1. DOMAIN MATCHING: First, analyze the metric names and sample context to determine the domain (e.g., Retail Sales, Product Inventory, Logistics, Tech specs).
2. INTUITIVE & CLEAR LABELS: Create strategic labels that are professional and easy to understand (McKinsey style but strictly grounded in what the column actually is).
   - If the metric is a sum of 'price' or 'cost', label it as 'Average List Price' or 'Total Operational Cost' (or similar), not abstract names like 'Realization Efficiency'.
   - If the metric is a sum of 'storage' or physical specs (e.g. phone hard drive space), label it as 'Total Product Storage' or 'Device Storage Capacity (GB)', never 'Computational Resource Capacity'.
   - If the metric is a row count or total quantity, label it as 'Total Transaction Count', 'Order Volume', or 'Inventory Count' instead of 'Data Asset Accumulation'.
   - The label MUST make immediate business sense to a general executive viewing this specific dataset.
3. STRATEGIC INSIGHTS: For each metric, explain the 'So What?'. Why does this matter for board-level decision-making? (15-20 words).

Output MUST be valid JSON with this structure:
[
  {
    "original_name": "metric_name",
    "impact_label": "Strategic Grounded Label",
    "insight": "Clear executive insight (15-20 words)."
  }
]"""

def call_gemini_with_retry(call_func, max_retries=3):
    """Executes a Gemini API call with automatic API key rotation and very fast retries."""
    for attempt in range(max_retries):
        try:
            return call_func()
        except Exception as e:
            err_str = str(e).lower()
            print(f"[DEBUG] API Error on attempt {attempt + 1}: {str(e)}")
            
            # Check for Rate Limit or Quota Exceeded
            if any(x in err_str for x in ["429", "resource_exhausted", "quota"]):
                if switch_api_key():
                    print("Key switched successfully. Retrying immediately...")
                    continue
                else:
                    if attempt < max_retries - 1:
                        print("Rate limit hit. Retrying in 2 seconds...")
                        time.sleep(2)
                        continue
            
            # Check for standard Server Errors (like 503)
            is_server_error = any(x in err_str for x in ["503", "unavailable", "500"])
            if is_server_error:
                if attempt < max_retries - 1:
                    print("Google Server Error. Retrying in 2 seconds...")
                    time.sleep(2)
                    continue
                    
            # If we reach here, we've exhausted retries or hit an unrecoverable error
            raise e

def get_ai_insight(message, data_summary, sample_data=None):
    """Connects to Gemini to generate strategic business insights or dynamic charts."""
    global API_KEY_VALID
    if not client or not API_KEY_VALID:
        return '{"type": "text", "message": "AI Analysis Error: API key is invalid or leaked. Please update your .env file."}'

    try:
        prompt = f"""You are an intelligent Executive Data Analyst Assistant. 
Data Context (Columns & Types): {data_summary}
Sample Data: {sample_data}

User Question: {message}

If the user is asking a general question about the data, analyze it and answer them clearly in professional text. 
Format as a JSON object: {{"type": "text", "message": "your answer"}}

If the user is explicitly asking you to generate, plot, or show a specific chart/graph, you MUST generate the configuration for it based strictly on the columns provided in Data Context.
Format as a JSON object: 
{{
  "type": "chart", 
  "message": "Here is the chart you requested.",
  "chart_config": {{
    "title": "Professional Chart Title",
    "type": "line" | "bar" | "doughnut" | "pie" | "polarArea" | "horizontalBar",
    "style": "standard" | "vertical" | "area" | "spline",
    "x_column": "exact_x_column_name_from_context",
    "y_column": "exact_y_column_name_from_context",
    "aggregation": "sum" | "mean" | "count"
  }}
}}

Output strictly valid JSON and nothing else.
"""
        response = call_gemini_with_retry(lambda: client.models.generate_content(
            model='gemini-2.5-flash',
            config=types.GenerateContentConfig(response_mime_type="application/json"),
            contents=[prompt]
        ))
        return response.text
    except Exception as e:
        err_str = str(e).upper()
        if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
            return "AI Analysis Error: Rate limit exceeded. Please wait a moment and try again."
        if any(x in err_str for x in ["403", "PERMISSION_DENIED", "LEAKED"]):
            API_KEY_VALID = False
            return "CRITICAL: AI API Key reported as leaked. AI features disabled."
        return f"AI Analysis Error: {str(e)}"

def clean_ai_json(text):
    """Cleans markdown formatting and other common AI output artifacts from JSON strings."""
    text = text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
    return text

def get_kpi_analysis(metrics_data):
    """Uses Gemini to generate strategic labels and insights for top KPIs."""
    global API_KEY_VALID
    if not client or not API_KEY_VALID:
        print("AI KPI SKIPPED: Client or Key Invalid")
        return []

    try:
        print(f"REQUESTING AI KPI ANALYSIS for {len(metrics_data)} metrics...")
        response = call_gemini_with_retry(lambda: client.models.generate_content(
            model="gemini-2.5-flash",
            config=types.GenerateContentConfig(
                system_instruction=EXPERT_PROMPT,
                response_mime_type="application/json"
            ),
            contents=[f"Analyze these organizational metrics: {json.dumps(metrics_data)}"]
        ))
        if response.text:
            cleaned = clean_ai_json(response.text)
            return json.loads(cleaned)
        return []
    except Exception as e:
        print(f"KPI AI ERROR: {e}")
        return []

def get_report_descriptions(charts_data):
    """Batch processes chart descriptions for the final report."""
    global API_KEY_VALID
    if not client or not API_KEY_VALID:
        return {}

    try:
        summary_data = []
        for c in charts_data[:15]:
            summary_data.append({
                "title": c.get('title'),
                "type": c.get('type'),
                "labels": c.get('labels')[:5]
            })

        print(f"REQUESTING BATCH DESCRIPTIONS for {len(summary_data)} charts...")
        prompt = f"""
        Act as a Lead Data Scientist and Strategic Consultant. 
        For these {len(summary_data)} visualizations, provide a deep-dive strategic analysis.
        
        REQUIREMENTS FOR EACH CHART:
        1. Format: EXACTLY 5 to 7 professional and distinct bullet points.
        2. Content: Provide direct, high-impact strategic insights based on quantitative trends, visual insights, business impact, strategic risks, and actionable steps.
           - Do NOT use explicit prefix labels like "Quantitative Trend:", "Visual Insight:", etc. Just provide the direct insight.
           - Keep the points concise and focused on the most important information.
        
        Output MUST be a VALID JSON object where:
        - Keys: The exact 'title' of the chart provided in the input.
        - Values: A single string containing all 5-7 bullet points, each starting with '• '.
        """
        
        response = call_gemini_with_retry(lambda: client.models.generate_content(
            model="gemini-2.5-flash",
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            ),
            contents=[prompt, json.dumps(summary_data)]
        ))
        if response.text:
            cleaned = clean_ai_json(response.text)
            ai_results = json.loads(cleaned)
            
            if isinstance(ai_results, list):
                new_results = {}
                for item in ai_results:
                    if isinstance(item, dict):
                        if 'title' in item:
                            val_keys = [k for k in item.keys() if k.lower() != 'title']
                            if val_keys:
                                new_results[item['title']] = item[val_keys[0]]
                        else:
                            new_results.update(item)
                ai_results = new_results
            
            # Robust Key Mapping: Gemini sometimes changes the title slightly
            final_results = {}
            for c in charts_data[:15]:
                orig_title = c.get('title', '')
                if not orig_title: continue
                
                # 1. Exact Match
                if orig_title in ai_results:
                    final_results[orig_title] = ai_results[orig_title]
                    continue
                
                # 2. Fuzzy Match (if Gemini dropped a prefix or suffix)
                matched = False
                for ai_key, ai_val in ai_results.items():
                    # Check if one is a substantial substring of the other
                    if len(ai_key) > 5 and (ai_key in orig_title or orig_title in ai_key):
                        final_results[orig_title] = ai_val
                        matched = True
                        break
                
                # 3. Fallback (if completely missed)
                if not matched:
                    unassigned = [v for k, v in ai_results.items() if k not in final_results.values()]
                    if unassigned:
                        final_results[orig_title] = unassigned[0]
                        ai_results = {k: v for k, v in ai_results.items() if v != unassigned[0]} # consume it
            
            # GUARANTEE CHECK: Fill any remaining missing charts with dynamic fallbacks
            for c in charts_data[:15]:
                orig_title = c.get('title', '')
                if orig_title and orig_title not in final_results:
                    final_results[orig_title] = _generate_dynamic_fallback(c)

            return final_results
        
        # If response was completely empty
        return {c.get('title', ''): _generate_dynamic_fallback(c) for c in charts_data[:15]}

    except Exception as e:
        print(f"BATCH DESCRIPTION ERROR: {e}")
        # ZERO-FAIL FALLBACK: Always return 5 bullet points per chart even if AI completely fails
        return {c.get('title', ''): _generate_dynamic_fallback(c) for c in charts_data[:15]}

def _generate_dynamic_fallback(chart_data):
    """Generates a professional 5-bullet strategic insight dynamically by analyzing raw chart data math."""
    t = chart_data.get('title', 'Metric Analysis')
    ctype = chart_data.get('type', 'data')
    labels = chart_data.get('labels', [])
    datasets = chart_data.get('datasets', [])
    
    # Mathematical Data Extraction
    max_val, min_val, total, dominant_label = 0, 0, 0, "Unknown"
    second_label, third_label = "", ""
    is_volatile = False
    gap_percent = 0
    
    if labels and datasets and len(datasets[0].get('data', [])) > 0:
        data_pts = datasets[0].get('data', [])
        valid_data = [float(x) for x in data_pts if str(x).replace('.','',1).isdigit() or (isinstance(x, (int, float)))]
        
        if valid_data:
            total = sum(valid_data)
            
            # Sort the pairs of (label, value) descending to get top 3
            paired = sorted(list(zip(labels, valid_data)), key=lambda x: x[1], reverse=True)
            
            max_val = paired[0][1]
            dominant_label = paired[0][0]
            
            if len(paired) > 1:
                second_label = paired[1][0]
            if len(paired) > 2:
                third_label = paired[2][0]
                
            min_val = paired[-1][1]
            
            if min_val > 0:
                gap_percent = round(((max_val - min_val) / min_val) * 100, 1)
                is_volatile = gap_percent > 50

    if dominant_label == "Unknown" or max_val == 0:
        return f"""• Detailed quantitative trend analysis is active for '{t}'.
• Distribution suggests stable baseline performance across all tracked segments.
• Core metrics align with historical operational benchmarks and projections.
• Continuous monitoring is advised to detect early signals of volatility.
• Actionable recommendation: Review segment-specific details to optimize margin contribution."""

    # Randomize Templates for Diversity
    import random
    templates = [
        # Template Set 1
        {
            "trend": f"The leading segment is '{dominant_label}' at {max_val:,.2f}, indicating a strong concentration in this area.",
            "insight": f"There is a substantial {gap_percent}% gap between the top and bottom performers." if is_volatile else f"Values remain relatively uniform across all {len(labels)} segments.",
            "impact": f"Because '{dominant_label}' is the primary driver, overall success is heavily dependent on it.",
            "risk": f"If '{dominant_label}' drops in performance, the entire metric will suffer. Diversification is necessary.",
            "action": "Investigate why lagging segments are underperforming and apply learnings from the top tier."
        },
        # Template Set 2
        {
            "trend": f"We see a clear peak at '{dominant_label}', which recorded {max_val:,.2f}, significantly outpacing the lower end.",
            "insight": f"The extreme variance of {gap_percent}% points to severe inconsistencies across segments." if is_volatile else f"The data shows a balanced distribution with no alarming outliers.",
            "impact": f"Secondary segments like '{second_label}' and '{third_label}' provide crucial supporting volume.",
            "risk": "A lack of balance means market shifts could disproportionately impact the top segment.",
            "action": "Consider resource reallocation to boost the middle-tier segments and reduce dependency."
        },
        # Template Set 3
        {
            "trend": f"'{dominant_label}' dominates the chart with a value of {max_val:,.2f}.",
            "insight": f"High volatility is present, with the lowest segment dropping {gap_percent}% below the peak." if is_volatile else f"Stability is high, as the {len(labels)} groups perform similarly.",
            "impact": f"The performance of '{dominant_label}' effectively masks any deficiencies in the lower tiers.",
            "risk": "Failing to optimize the bottom segments leaves untapped potential on the table.",
            "action": "Launch targeted interventions for the lowest performing groups to lift the overall average."
        }
    ]
    
    choice = random.choice(templates)
    
    return f"""• {choice["trend"]}
• {choice["insight"]}
• {choice["impact"]}
• {choice["risk"]}
• {choice["action"]}"""


CHART_ARCHITECT_PROMPT = """# Advanced Chart Diversity & Selection Rules for AI Analytics Engine

## Objective
You are an **Expert Business Intelligence Architect and Senior Data Visualization Consultant** responsible for designing the most meaningful, diverse, and executive-ready visualizations for any uploaded dataset.

Your goal is to generate the **maximum number of UNIQUE, BUSINESS-RELEVANT, and NON-REDUNDANT visualizations** that provide different insights.

---

# PRIMARY RULE: Every Chart Must Answer a Different Question
Each chart must provide a completely different analytical perspective.

# Mandatory Chart Diversity Policy
Use every chart type **at most ONE time** until every available chart type has been exhausted.

Preferred generation order:
1. Bar Chart (vertical)
2. Line Chart
3. Horizontal Bar Chart
4. Doughnut Chart
5. Pie Chart
6. Polar Area Chart

Only after every unique chart type has been used may a chart type be repeated.

Maximum allowed repetitions:
Bar Chart: Maximum 5
Line Chart: Maximum 4
Horizontal Bar Chart: Maximum 4
Doughnut Chart: Maximum 2
Pie Chart: Maximum 2
Polar Area Chart: Maximum 2

If this rule is violated, regenerate the chart list.

---

# Chart Selection Intelligence
Select charts according to the detected data structure.

## Bar Chart & Horizontal Bar Chart
Use when:
* Comparing categories
* Rankings
* Top/Bottom performers
* Product comparisons
* Regional analysis

## Line Chart
Use only when:
* Date columns exist
* Time series analysis is possible
* Trend analysis is meaningful
Never use Line Charts for unordered categorical data.

## Doughnut Chart & Pie Chart
Use when percentage contribution is important.
NEVER use Doughnut or Pie charts for Date/Time columns (X-axis).
Never generate Pie and Doughnut charts for exactly the same columns.

## Polar Area Chart
Use for comparing magnitude across categories where circular visualization provides additional insight.

---

# Semantic Uniqueness Rule (CRITICAL FOR DIVERSITY)
You MUST generate visually and structurally diverse charts. 
Charts are considered duplicates if they use the exact same X-axis AND Y-axis columns. 
You MUST rotate through all available numeric and categorical columns in the dataset.
Do not just change the title; change the actual data columns being plotted!

# QUALITY CONTROL: NO BORING FLAT CHARTS
1. NEVER plot a continuous flat variable against Time/Dates (e.g., plotting "Fuel Price" or "CPI" over Time). This creates an unreadable flat line.
2. ALWAYS prefer AGGREGATION: Group a continuous variable by a categorical bucket (e.g., "Total Sales by Region", "Average Salary by Department"). This is what Pie, Doughnut, and Bar charts are for.
3. Only use Line charts for highly volatile metrics that have significant variance over time (e.g., "Daily Active Users", "Total Revenue").

---

# Output Validation
Before returning results, validate:
□ Total charts between 15 and 20 (MAXIMIZE output)
□ At least 12 unique business questions answered
□ Uses as many different columns from the dataset as possible
□ No duplicate X-Y column combinations

Output MUST be a valid JSON array containing the chart design objects:
[
  {
    "title": "Chart Title (Strategic Style)",
    "type": "line" | "bar" | "doughnut" | "pie" | "polarArea" | "horizontalBar",
    "style": "standard" | "vertical" | "area" | "spline",
    "x_column": "exact_x_col_name",
    "y_column": "exact_y_col_name",
    "aggregation": "sum" | "mean" | "count"
  }
]"""

def design_semantic_charts(columns_metadata, sample_rows):
    """
    Connects to Gemini to design 6 high-value charts tailored to the uploaded dataset's schema.
    """
    global API_KEY_VALID
    if not client or not API_KEY_VALID:
        print("AI CHART ARCHITECT SKIPPED: Client or Key Invalid")
        return []

    try:
        payload = {
            "columns": columns_metadata,
            "sample_data": sample_rows[:5] # Send up to 5 sample rows for semantic context
        }
        
        print("REQUESTING AI CHART DESIGNS from Gemini...")
        response = call_gemini_with_retry(lambda: client.models.generate_content(
            model="gemini-2.5-flash",
            config=types.GenerateContentConfig(
                system_instruction=CHART_ARCHITECT_PROMPT,
                response_mime_type="application/json"
            ),
            contents=[f"Analyze this dataset schema and design AS MANY highly-relevant, unique charts AS APPROPRIATE based strictly on the content: {json.dumps(payload)}"]
        ))
        
        if response.text:
            cleaned = clean_ai_json(response.text)
            charts_design = json.loads(cleaned)
            if isinstance(charts_design, list) and len(charts_design) > 0:
                print(f"SUCCESS: AI designed {len(charts_design)} semantic charts dynamically!")
                return charts_design
        return []
    except Exception as e:
        print(f"AI CHART ARCHITECT ERROR: {e}")
        return []

STRATEGIC_ACTION_PROMPT = """You are a Senior Strategic McKinsey Consultant and Chief Strategy Officer.
Your task is to analyze the high-level KPI metrics summary and sample data rows of an uploaded dataset and generate 3 to 4 concrete, highly actionable, and dollar-quantified strategic action plans to help executives optimize their business.

GUIDELINES:
1. QUANTIFIED B2B IMPACTS: Assign a realistic, quantified B2B financial impact badge to each card (e.g. '+$12.5K Opportunity', '-5.2% Cost Reduction', '+$24K Sales Boost', '+14.5% SKU Volume').
2. ACTIONABLE & SPECIFIC: Each action card must address a specific operational strategy based on columns in the dataset (e.g., Return Mitigation, Margin Recovery, Understock Management).
3. THREE DIRECT STEPS: Provide exactly 3 clear, step-by-step checklist items that an executive can review and check off.

Output MUST be a valid JSON array of 3-4 objects:
[
  {
    "title": "Strategy Title (e.g., Dynamic Markdown Optimization)",
    "impact": "+$18.2K Opportunity",
    "description": "A clear overview of the strategy (15-20 words).",
    "steps": [
      "Checklist item step 1...",
      "Checklist item step 2...",
      "Checklist item step 3..."
    ]
  }
]"""

def get_strategic_actions(metrics_summary, sample_rows):
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
            model="gemini-2.5-flash",
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

MASTER_INTELLIGENCE_PROMPT = """# Advanced AI Business Intelligence Engine

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
"""

def generate_master_intelligence(metrics_data, columns_metadata, sample_rows):
    """
    Connects to Gemini to generate KPIs, Charts, Descriptions, and Actions in ONE single API call.
    """
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
            model="gemini-2.5-flash",
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
