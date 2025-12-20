import dash
from dash import dcc, html, dash_table, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv
from datetime import datetime
import numpy as np

load_dotenv()

# Initialize Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.FONT_AWESOME])
server = app.server
app.title = "Tax Summit Analytics Dashboard"
app.config['suppress_callback_exceptions'] = True

# Database connection
def get_db_connection():
    try:
        # Check if Railway-specific variables exist
        railway_host = os.getenv("MYSQLHOST")
        
        if railway_host:
            # Running on Railway - use Railway's MySQL variables
            host = railway_host
            user = os.getenv("MYSQLUSER")
            password = os.getenv("MYSQLPASSWORD")
            database = os.getenv("MYSQLDATABASE")
            port = int(os.getenv("MYSQLPORT", 3306))
            print(f"🚂 Connecting to Railway MySQL: {host}:{port}/{database}")
        else:
            # Running locally - use custom variables
            host = os.getenv("DB_HOST")
            user = os.getenv("DB_USER")
            password = os.getenv("DB_PASS")
            database = os.getenv("DB_NAME")
            port = int(os.getenv("DB_PORT", 3306))
            print(f"💻 Connecting to Local MySQL: {host}:{port}/{database}")
        
        connection = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            port=port
        )
        
        if connection.is_connected():
            print("✅ Database connection successful!")
            return connection
            
    except Error as e:
        print(f"❌ Database connection failed: {e}")
        return None

def fetch_master_data():
    conn = get_db_connection()
    if conn:
        table_name = os.getenv("DB_TABLE", "tax_summit_master_data")
        df = pd.read_sql(f"SELECT * FROM {table_name}", conn)
        conn.close()
        return df
    return pd.DataFrame()

def fetch_analysis_tables():
    conn = get_db_connection()
    if not conn:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    
    try:
        # Try lowercase first (Railway), then uppercase (local)
        try:
            tax_df = pd.read_sql("SELECT * FROM tax_persons_analysis", conn)
        except:
            tax_df = pd.read_sql("SELECT * FROM Tax_Persons_Analysis", conn)
        
        try:
            cfo_df = pd.read_sql("SELECT * FROM cfo_persons_analysis", conn)
        except:
            cfo_df = pd.read_sql("SELECT * FROM CFO_Persons_Analysis", conn)
        
        try:
            other_df = pd.read_sql("SELECT * FROM other_persons_analysis", conn)
        except:
            other_df = pd.read_sql("SELECT * FROM Other_Persons_Analysis", conn)
        
        conn.close()
        return tax_df, cfo_df, other_df
        
    except Exception as e:
        print(f"❌ Error fetching analysis tables: {e}")
        if conn:
            conn.close()
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# Utility functions
def safe_int(val):
    """Safely convert value to int"""
    try:
        if pd.isna(val) or val == '' or val is None:
            return 0
        return int(float(str(val)))
    except:
        return 0

def calculate_conversion_rate(registrations, invitees):
    invitees = safe_int(invitees)
    registrations = safe_int(registrations)
    return round((registrations / invitees * 100), 2) if invitees > 0 else 0

COLORS = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f']

def get_region(location):
    """Map location to region"""
    if pd.isna(location) or location is None:
        return 'Unknown'
    location = str(location).strip().title()
    
    # Define region mappings based on actual data
    north = ['Delhi', 'New Delhi', 'Gurugram', 'Gurgaon', 'Noida', 'Faridabad', 'Manesar', 'Bawal']
    
    south = ['Bangalore', 'Chennai', 'Hyderabad', 'Visakhapatnam', 'Kochi', 'Mangalore', 
             'Tirupati', 'Chengalpattu']
    
    east = ['Kolkata', 'Jamshedpur', 'Orrisa', 'Odisha']
    
    west = ['Mumbai', 'Pune', 'Ahmedabad', 'Surat', 'Aurangabad', 'Silvassa', 'Maharashtra', 
            'Nagpur', 'Kota', 'Udaipur', 'Wasim', 'Vapi']
    
    # Note: Paris is international, will go to 'Other'
    
    for city in north:
        if city.lower() in location.lower():
            return 'North'
    for city in south:
        if city.lower() in location.lower():
            return 'South'
    for city in east:
        if city.lower() in location.lower():
            return 'East'
    for city in west:
        if city.lower() in location.lower():
            return 'West'
    
    return 'Other' # Covers international and unmapped locations

# To normalize response labels
def normalize_response_label(response):
    """Normalize response labels by removing numeric prefixes"""
    if pd.isna(response) or response is None:
        return response
    
    response_str = str(response).strip().title()
    
    # Remove numeric prefixes like "2 Positive" -> "Positive"
    import re
    match = re.match(r'^(\d+)\s+(.+)$', response_str)
    if match:
        return match.group(2)  # Return just the label part
    
    return response_str


# To handle the weight/multiplier in responses like "2 Positive" or any other numeric prefix
def get_response_weight(response):
    """Get the weight/multiplier for a response (e.g., '2 Positive' returns 2)"""
    if pd.isna(response) or response is None:
        return 1
    
    response_str = str(response).strip()
    
    # Extract numeric prefix
    import re
    match = re.match(r'^(\d+)\s+', response_str)
    if match:
        return int(match.group(1))
    
    return 1  # Default weight is 1

# Function to filter analysis tables based on master data filters
def filter_analysis_table(analysis_df, filtered_master_df, practice_head_col='Practice_Head', partner_col='Partner'):
    """Filter analysis table based on filtered master data"""
    if analysis_df.empty or filtered_master_df.empty:
        return analysis_df
    
    # Get unique Practice Heads and Partners from filtered master data
    filtered_phs = filtered_master_df[practice_head_col].dropna().unique()
    filtered_partners = filtered_master_df[partner_col].dropna().unique()
    
    # Filter analysis table
    filtered_analysis = analysis_df[
        (analysis_df[practice_head_col].isin(filtered_phs)) & 
        (analysis_df[partner_col].isin(filtered_partners))
    ].copy()
    
    return filtered_analysis

# Layout components
def create_summary_card(title, value, icon, color="primary"):
    return dbc.Card([
        dbc.CardBody([
            html.Div([
                html.P(title, className="text-muted mb-1 small"),
                html.H4(str(value), className=f"text-{color} mb-0 fw-bold"),
                html.I(className=f"fas fa-{icon} position-absolute", 
                      style={'right': '15px', 'top': '15px', 'fontSize': '24px', 'opacity': '0.3'})
            ])
        ])
    ], className=f"border-start border-{color} border-4 h-100 shadow-sm")

def create_filter_panel():
    return dbc.Card([
        dbc.CardHeader(html.H5([html.I(className="fas fa-filter me-2"), "Filters"], className="mb-0")),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Label("Practice Head", className="fw-bold small"),
                    dcc.Dropdown(id='practice-head-filter', multi=True, placeholder="All")
                ], md=3),
                dbc.Col([
                    html.Label("Partner", className="fw-bold small"),
                    dcc.Dropdown(id='partner-filter', multi=True, placeholder="All")
                ], md=3),
                dbc.Col([
                    html.Label("Sector", className="fw-bold small"),
                    dcc.Dropdown(id='sector-filter', multi=True, placeholder="All")
                ], md=3),
                dbc.Col([
                    html.Label("Location", className="fw-bold small"),
                    dcc.Dropdown(id='location-filter', multi=True, placeholder="All")
                ], md=3),
            ], className="mb-2"),
            dbc.Row([
                dbc.Col([
                    html.Label("Response Status", className="fw-bold small"),
                    dcc.Dropdown(id='response-filter', multi=True, placeholder="All")
                ], md=3),
                dbc.Col([
                    dbc.Button([html.I(className="fas fa-check me-2"), "Apply"], 
                              id="apply-filters", color="primary", size="sm", className="mt-4 w-100")
                ], md=2),
                dbc.Col([
                    dbc.Button([html.I(className="fas fa-redo me-2"), "Reset"], 
                              id="reset-filters", color="secondary", size="sm", className="mt-4 w-100")
                ], md=2),
                dbc.Col([
                    html.Div([
                        html.Span("Auto-refresh: 30s", className="badge bg-success mt-4"),
                        dcc.Interval(id='interval-component', interval=30*1000, n_intervals=0)
                    ])
                ], md=2, className="text-end"),
            ])
        ])
    ], className="mb-4 shadow-sm")

# Below is a commented-out function for creating data tables, which has been removed from use.
# def create_data_table(df, table_id):
#     if df.empty:
#         return html.Div("No data available", className="text-muted text-center p-4")
    
#     return html.Div([
#         dbc.Row([
#             dbc.Col(html.H6([html.I(className="fas fa-table me-2"), "Detailed Data"], className="mb-3"), md=9),
#             dbc.Col(dbc.Button([html.I(className="fas fa-file-excel me-2"), "Export"], 
#                               id=f"{table_id}-export", color="success", size="sm", className="w-100"), md=3)
#         ]),
#         dash_table.DataTable(
#             id=table_id,
#             columns=[{"name": i, "id": i} for i in df.columns],
#             data=df.to_dict('records'),
#             page_size=10,
#             style_table={'overflowX': 'auto'},
#             style_cell={'textAlign': 'left', 'padding': '8px', 'fontSize': '12px'},
#             style_header={'backgroundColor': '#2c3e50', 'color': 'white', 'fontWeight': 'bold'},
#             style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#f8f9fa'}],
#             filter_action="native",
#             sort_action="native",
#             sort_mode="multi"
#         ),
#         dcc.Download(id=f"{table_id}-download")
#     ], className="mt-4")

# Main layout
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H2([html.I(className="fas fa-chart-line me-3"), "Tax Summit Analytics Dashboard"], 
                   className="text-primary mb-0"),
            html.P("Real-time insights and performance metrics", className="text-muted small")
        ])
    ], className="mb-4 mt-3"),
    
    create_filter_panel(),
    
    dbc.Tabs([
        dbc.Tab(label="📊 Overview", tab_id="overview"),
        dbc.Tab(label="👔 Practice Head", tab_id="practice-head"),
        dbc.Tab(label="🤝 Partner", tab_id="partner"),
        dbc.Tab(label="💼 Tax Contacts", tab_id="tax"),
        dbc.Tab(label="💰 CFO Contacts", tab_id="cfo"),
        dbc.Tab(label="👥 Other Contacts", tab_id="other"),
        dbc.Tab(label="📈 Metrics", tab_id="metrics"),
    ], id="tabs", active_tab="overview", className="mb-4"),
    
    html.Div(id="tab-content"),
    
    dcc.Store(id='master-data'),
    dcc.Store(id='tax-data'),
    dcc.Store(id='cfo-data'),
    dcc.Store(id='other-data'),
    dcc.Store(id='filtered-data'),
    dcc.Store(id='current-filters') # Store Current filter values
], fluid=True, style={'backgroundColor': '#f8f9fa', 'minHeight': '100vh'})

# Callbacks
@app.callback(
    [Output('practice-head-filter', 'options'),
     Output('partner-filter', 'options'),
     Output('sector-filter', 'options'),
     Output('location-filter', 'options'),
     Output('response-filter', 'options'),
     Output('master-data', 'data'),
     Output('tax-data', 'data'),
     Output('cfo-data', 'data'),
     Output('other-data', 'data')],
    Input('interval-component', 'n_intervals')
)
def load_data(n):
    master_df = fetch_master_data()
    tax_df, cfo_df, other_df = fetch_analysis_tables()
    
    # Standardize names to Title format
    if not master_df.empty:
        name_columns = ['Practice_Head', 'Partner', 'Client_Name', 'Location', 'Sector']
        for col in name_columns:
            if col in master_df.columns:
                master_df[col] = master_df[col].apply(lambda x: str(x).strip().title() if pd.notna(x) else x)
    
    if not tax_df.empty:
        name_columns = ['Practice_Head', 'Partner', 'Client_Name', 'Location', 'Sector', 'Person_Name']
        for col in name_columns:
            if col in tax_df.columns:
                tax_df[col] = tax_df[col].apply(lambda x: str(x).strip().title() if pd.notna(x) else x)
    
    if not cfo_df.empty:
        name_columns = ['Practice_Head', 'Partner', 'Client_Name', 'Location', 'Sector', 'Person_Name']
        for col in name_columns:
            if col in cfo_df.columns:
                cfo_df[col] = cfo_df[col].apply(lambda x: str(x).strip().title() if pd.notna(x) else x)
    
    if not other_df.empty:
        name_columns = ['Practice_Head', 'Partner', 'Client_Name', 'Location', 'Sector', 'Person_Name']
        for col in name_columns:
            if col in other_df.columns:
                other_df[col] = other_df[col].apply(lambda x: str(x).strip().title() if pd.notna(x) else x)
    
        # After standardizing master_df
    if not master_df.empty and 'Response' in master_df.columns:
        master_df['Response_Weight'] = master_df['Response'].apply(get_response_weight)
        master_df['Response'] = master_df['Response'].apply(normalize_response_label)

    # After standardizing tax_df
    if not tax_df.empty and 'Response' in tax_df.columns:
        tax_df['Response_Weight'] = tax_df['Response'].apply(get_response_weight)
        tax_df['Response'] = tax_df['Response'].apply(normalize_response_label)

    # After standardizing cfo_df
    if not cfo_df.empty and 'Response' in cfo_df.columns:
        cfo_df['Response_Weight'] = cfo_df['Response'].apply(get_response_weight)
        cfo_df['Response'] = cfo_df['Response'].apply(normalize_response_label)

    # After standardizing other_df
    if not other_df.empty and 'Response' in other_df.columns:
        other_df['Response_Weight'] = other_df['Response'].apply(get_response_weight)
        other_df['Response'] = other_df['Response'].apply(normalize_response_label)
    
    if master_df.empty:
        return [], [], [], [], [], {}, {}, {}, {}
    
    ph_opts = [{'label': x, 'value': x} for x in sorted(master_df['Practice_Head'].dropna().unique())]
    partner_opts = [{'label': x, 'value': x} for x in sorted(master_df['Partner'].dropna().unique())]
    sector_opts = [{'label': x, 'value': x} for x in sorted(master_df['Sector'].dropna().unique())]
    loc_opts = [{'label': x, 'value': x} for x in sorted(master_df['Location'].dropna().unique())]
    resp_opts = [{'label': x, 'value': x} for x in sorted(master_df['Response'].dropna().unique())]
    
    return (ph_opts, partner_opts, sector_opts, loc_opts, resp_opts, 
            master_df.to_dict('records'), tax_df.to_dict('records'), 
            cfo_df.to_dict('records'), other_df.to_dict('records'))

# MODIFIED: Filter data callback now also responds to tab changes
@app.callback(
    Output('filtered-data', 'data'),
    [Input('master-data', 'data'),
     Input('current-filters', 'data'),
     Input('tabs', 'active_tab')],  # NEW: Added tab as input
)
def filter_data(data, filters, active_tab):
    if not data or not filters:
        return data if data else []
    
    df = pd.DataFrame(data)
    
    # Apply filters if they exist
    if filters.get('ph'):
        df = df[df['Practice_Head'].isin(filters['ph'])]
    if filters.get('partner'):
        df = df[df['Partner'].isin(filters['partner'])]
    if filters.get('sector'):
        df = df[df['Sector'].isin(filters['sector'])]
    if filters.get('loc'):
        df = df[df['Location'].isin(filters['loc'])]
    if filters.get('resp'):
        df = df[df['Response'].isin(filters['resp'])]
    
    return df.to_dict('records')

# NEW: Reset filter values in UI
@app.callback(
    [Output('practice-head-filter', 'value'),
     Output('partner-filter', 'value'),
     Output('sector-filter', 'value'),
     Output('location-filter', 'value'),
     Output('response-filter', 'value')],
    Input('reset-filters', 'n_clicks'),
    prevent_initial_call=True
)
def reset_filter_values(n_clicks):
    return None, None, None, None, None


@app.callback(
    Output('current-filters', 'data'),
    [Input('apply-filters', 'n_clicks'),
     Input('reset-filters', 'n_clicks')],
    [State('practice-head-filter', 'value'),
     State('partner-filter', 'value'),
     State('sector-filter', 'value'),
     State('location-filter', 'value'),
     State('response-filter', 'value')],
    prevent_initial_call=True
)
def update_filters(apply_clicks, reset_clicks, ph, partner, sector, loc, resp):
    """Store current filter values when Apply or Reset is clicked"""
    ctx = callback_context
    
    if not ctx.triggered:
        return {}
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    # If Reset was clicked, return empty filters
    if button_id == 'reset-filters':
        return {
            'ph': [],
            'partner': [],
            'sector': [],
            'loc': [],
            'resp': []
        }
    
    # If Apply was clicked, store current values
    return {
        'ph': ph or [],
        'partner': partner or [],
        'sector': sector or [],
        'loc': loc or [],
        'resp': resp or []
    }

@app.callback(
    Output('tab-content', 'children'),
    [Input('tabs', 'active_tab'), 
     Input('filtered-data', 'data'),
     Input('master-data', 'data'),
     Input('tax-data', 'data'), 
     Input('cfo-data', 'data'), 
     Input('other-data', 'data')]
)

def render_content(tab, filtered, master, tax, cfo, other):
    if not filtered:
        return html.Div("Loading...", className="text-center p-5")
    
    df = pd.DataFrame(filtered)
    master_df = pd.DataFrame(master) if master else df  # Fallback to filtered if master not available
    tax_df = pd.DataFrame(tax)
    cfo_df = pd.DataFrame(cfo)
    other_df = pd.DataFrame(other)
    
    # NEW: Filter analysis tables based on filtered master data
    filtered_tax_df = filter_analysis_table(tax_df, df)
    filtered_cfo_df = filter_analysis_table(cfo_df, df)
    filtered_other_df = filter_analysis_table(other_df, df)
    
    if tab == "overview":
        return create_overview_tab(df)
    elif tab == "practice-head":
        return create_practice_head_tab(df, filtered_tax_df, filtered_cfo_df, filtered_other_df)
    elif tab == "partner":
        return create_partner_tab(df, filtered_tax_df, filtered_cfo_df, filtered_other_df)
    elif tab == "tax":
        return create_tax_tab(filtered_tax_df)
    elif tab == "cfo":
        return create_cfo_tab(filtered_cfo_df)
    elif tab == "other":
        return create_other_tab(filtered_other_df)
    elif tab == "metrics":
        return create_metrics_tab(df)

def create_overview_tab(df):
    if df.empty:
        return html.div('No Data Available for current filters', className = 'text-muted text-center p-5')
    
    total_invites = len(df)
    total_invitees = df['numInvitees'].apply(safe_int).sum()
    total_reg = df['numRegistrations'].apply(safe_int).sum()
    resp_rate = round((df['Response'].notna().sum() / len(df) * 100), 2) if len(df) > 0 else 0
    
    # Weighted response distribution
    resp_dist = df.groupby('Response')['Response_Weight'].sum()
    
    sector_perf = df.groupby('Sector').agg({
        'numInvitees': lambda x: x.apply(safe_int).sum(),
        'numRegistrations': lambda x: x.apply(safe_int).sum()
    }).reset_index()
    sector_perf['Conversion'] = sector_perf.apply(
        lambda r: calculate_conversion_rate(r['numRegistrations'], r['numInvitees']), axis=1
    )

    # Add region analysis - filter out None/NaN locations first
    df_with_location = df[df['Location'].notna()].copy()
    df_with_location['Region'] = df_with_location['Location'].apply(get_region)
    
    region_counts = df_with_location['Region'].value_counts().reset_index()
    region_counts.columns = ['Region', 'Count']
    
    return html.Div([
        dbc.Row([
            dbc.Col(create_summary_card("Total Clients", f"{total_invites:,}", "envelope", "primary"), md=3),
            dbc.Col(create_summary_card("Total Invitees", f"{total_invitees:,}", "users", "info"), md=3),
            dbc.Col(create_summary_card("Registrations", f"{total_reg:,}", "check-circle", "success"), md=3),
            dbc.Col(create_summary_card("Response Rate", f"{resp_rate}%", "percentage", "warning"), md=3),
        ], className="mb-4"),
        
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Response Distribution"),
                    dbc.CardBody(dcc.Graph(figure=px.pie(values=resp_dist.values, names=resp_dist.index, hole=0.4)))
                ], className="shadow-sm")
            ], md=4),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Sector Performance"),
                    dbc.CardBody(dcc.Graph(figure=px.bar(sector_perf, x='Sector', y='Conversion', 
                                                        color='Conversion', color_continuous_scale='Viridis')))
                ], className="shadow-sm")
            ], md=4),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Region-wise Distribution"),
                    dbc.CardBody(dcc.Graph(figure=px.bar(region_counts, x='Region', y='Count',
                                                          color='Region', color_discrete_sequence=COLORS)))
                ], className="shadow-sm")
            ], md=4),
        ])
        
    ])


# Group by Practice Head
def create_practice_head_tab(df, tax_df, cfo_df, other_df):
    # To show when there is no output in Practice Head Tab
    if df.empty:
        return html.Div("No data available for current filters", className="text-muted text-center p-5")
    
    ph_stats = df.groupby('Practice_Head').agg({
        'Client_Name': 'count',
        'numInvitees': lambda x: x.apply(safe_int).sum(),
        'numRegistrations': lambda x: x.apply(safe_int).sum(),
        'Response': lambda x: x.notna().sum()
    }).reset_index()
    ph_stats.columns = ['Practice_Head', 'Invites_Sent', 'Invitees', 'Registrations', 'Responses']
    
    response_by_ph = df.groupby(['Practice_Head', 'Response'])['Response_Weight'].sum().reset_index(name='Count')
    sector_by_ph = df.groupby(['Practice_Head', 'Sector']).size().reset_index(name='Count')
    location_by_ph = df.groupby(['Practice_Head', 'Location']).size().reset_index(name='Count')
    
    # Handle empty dataframes for designation analysis
    if not cfo_df.empty:
        cfo_by_ph = cfo_df.groupby(['Practice_Head', 'Response'])['Response_Weight'].sum().reset_index(name='Count')
    else:
        cfo_by_ph = pd.DataFrame(columns=['Practice_Head', 'Response', 'Count'])
    
    if not tax_df.empty:
        tax_by_ph = tax_df.groupby(['Practice_Head', 'Response'])['Response_Weight'].sum().reset_index(name='Count')
    else:
        tax_by_ph = pd.DataFrame(columns=['Practice_Head', 'Response', 'Count'])
    
    if not other_df.empty:
        other_by_ph = other_df.groupby(['Practice_Head', 'Response'])['Response_Weight'].sum().reset_index(name='Count')
    else:
        other_by_ph = pd.DataFrame(columns=['Practice_Head', 'Response', 'Count'])

    return html.Div([
        html.H4("Practice Head Analysis", className="mb-4"),
        
        dbc.Row([
            dbc.Col(create_summary_card("Total Clients", ph_stats['Invites_Sent'].sum(), "paper-plane", "primary"), md=3),
            dbc.Col(create_summary_card("Total Invitees", ph_stats['Invitees'].sum(), "users", "info"), md=3),
            dbc.Col(create_summary_card("Total Responses", ph_stats['Responses'].sum(), "comments", "warning"), md=3),
            dbc.Col(create_summary_card("Total Registrations", ph_stats['Registrations'].sum(), "check", "success"), md=3),
        ], className="mb-4"),
        
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Invites & Registrations by Practice Head"),
                    dbc.CardBody(dcc.Graph(figure=go.Figure(data=[
                        go.Bar(name='Invites', x=ph_stats['Practice_Head'], y=ph_stats['Invites_Sent']),
                        go.Bar(name='Registrations', x=ph_stats['Practice_Head'], y=ph_stats['Registrations'])
                    ]).update_layout(barmode='group')))
                ], className="shadow-sm mb-4")
            ], md=12),
        ]),
        
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Response Split by Practice Head"),
                    dbc.CardBody(dcc.Graph(figure=px.bar(response_by_ph, x='Practice_Head', y='Count', 
                                                        color='Response', barmode='stack')))
                ], className="shadow-sm")
            ], md=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Sector Distribution"),
                    dbc.CardBody(dcc.Graph(figure=px.sunburst(sector_by_ph, path=['Practice_Head', 'Sector'], 
                                                             values='Count')))
                ], className="shadow-sm")
            ], md=6),
        ], className="mb-4"),
        
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Location Split"),
                    dbc.CardBody(dcc.Graph(figure=px.bar(location_by_ph, x='Practice_Head', y='Count', 
                                                        color='Location', barmode='stack')))
                ], className="shadow-sm")
            ], md=12),
        ], className="mb-4"),
        
        html.H5("Designation-wise Analysis", className="mt-4 mb-3"),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Tax Profiles - Response Split"),
                    dbc.CardBody(dcc.Graph(figure=px.bar(tax_by_ph, x='Practice_Head', y='Count', 
                                                        color='Response', barmode='group')))
                ], className="shadow-sm")
            ], md=4),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("CFO Profiles - Response Split"),
                    dbc.CardBody(dcc.Graph(figure=px.bar(cfo_by_ph, x='Practice_Head', y='Count', 
                                                        color='Response', barmode='group')))
                ], className="shadow-sm")
            ], md=4),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Other Profiles - Response Split"),
                    dbc.CardBody(dcc.Graph(figure=px.bar(other_by_ph, x='Practice_Head', y='Count', 
                                                        color='Response', barmode='group')))
                ], className="shadow-sm")
            ], md=4),
        ], className="mb-4"),
    ])

# Group by Partner Name
def create_partner_tab(df, tax_df, cfo_df, other_df):

    # To show where there is not output in Partners Tab
    if df.empty:
        return html.Div("No data available for current filters", className="text-muted text-center p-5")

    partner_stats = df.groupby('Partner').agg({
        'Client_Name': 'count',
        'numInvitees': lambda x: x.apply(safe_int).sum(),
        'numRegistrations': lambda x: x.apply(safe_int).sum(),
        'Response': lambda x: x.notna().sum()
    }).reset_index()
    partner_stats.columns = ['Partner', 'Invites_Sent', 'Invitees', 'Registrations', 'Responses']
    
    response_by_partner = df.groupby(['Partner', 'Response'])['Response_Weight'].sum().reset_index(name='Count')
    location_by_partner = df.groupby(['Partner', 'Location']).size().reset_index(name='Count')
    
    #Handle empty dataframes for designation analysis
    if not tax_df.empty:
        tax_by_partner = tax_df.groupby(['Partner', 'Response'])['Response_Weight'].sum().reset_index(name='Count')
    else:
        tax_by_partner = pd.DataFrame(columns=['Partner', 'Response', 'Count'])
    
    if not cfo_df.empty:
        cfo_by_partner = cfo_df.groupby(['Partner', 'Response'])['Response_Weight'].sum().reset_index(name='Count')
    else:
        cfo_by_partner = pd.DataFrame(columns=['Partner', 'Response', 'Count'])
    
    if not other_df.empty:
        other_by_partner = other_df.groupby(['Partner', 'Response'])['Response_Weight'].sum().reset_index(name='Count')
    else:
        other_by_partner = pd.DataFrame(columns=['Partner', 'Response', 'Count'])

    return html.Div([
        html.H4("Partner Analysis", className="mb-4"),
        
        dbc.Row([
            dbc.Col(create_summary_card("Total Clients", partner_stats['Invites_Sent'].sum(), "paper-plane", "primary"), md=3),
            dbc.Col(create_summary_card("Total Invitees", partner_stats['Invitees'].sum(), "users", "info"), md=3),
            dbc.Col(create_summary_card("Total Responses", partner_stats['Responses'].sum(), "comments", "warning"), md=3),
            dbc.Col(create_summary_card("Total Registrations", partner_stats['Registrations'].sum(), "check", "success"), md=3),
        ], className="mb-4"),
        
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Performance by Partner"),
                    dbc.CardBody(dcc.Graph(figure=go.Figure(data=[
                        go.Bar(name='Invites', x=partner_stats['Partner'], y=partner_stats['Invites_Sent']),
                        go.Bar(name='Registrations', x=partner_stats['Partner'], y=partner_stats['Registrations'])
                    ]).update_layout(barmode='group')))
                ], className="shadow-sm mb-4")
            ], md=12),
        ]),
        
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Response Split by Partner"),
                    dbc.CardBody(dcc.Graph(figure=px.bar(response_by_partner, x='Partner', y='Count', 
                                                        color='Response', barmode='stack')))
                ], className="shadow-sm")
            ], md=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Location Distribution"),
                    dbc.CardBody(dcc.Graph(figure=px.bar(location_by_partner, x='Partner', y='Count', 
                                                        color='Location', barmode='stack')))
                ], className="shadow-sm")
            ], md=6),
        ], className="mb-4"),
        
        html.H5("Designation-wise Analysis", className="mt-4 mb-3"),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Tax Profiles"),
                    dbc.CardBody(dcc.Graph(figure=px.bar(tax_by_partner, x='Partner', y='Count', 
                                                        color='Response', barmode='group')))
                ], className="shadow-sm")
            ], md=4),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("CFO Profiles"),
                    dbc.CardBody(dcc.Graph(figure=px.bar(cfo_by_partner, x='Partner', y='Count', 
                                                        color='Response', barmode='group')))
                ], className="shadow-sm")
            ], md=4),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Other Profiles"),
                    dbc.CardBody(dcc.Graph(figure=px.bar(other_by_partner, x='Partner', y='Count', 
                                                        color='Response', barmode='group')))
                ], className="shadow-sm")
            ], md=4),
        ], className="mb-4"),
        
    ])

def create_tax_tab(tax_df):
    # To show when where there is no output in Tax Tab
    if tax_df.empty:
        return html.Div("No data available for current filters", className="text-muted text-center p-5")

    total = len(tax_df)
    registered = len(tax_df[tax_df['Response_1'].str.lower() == 'registered'])
    responses = tax_df.groupby('Response')['Response_Weight'].sum()
    
    # Region analysis for Tax contacts
    tax_df_with_location = tax_df[tax_df['Location'].notna()].copy()
    tax_df_with_location['Response_Clean'] = tax_df_with_location['Response_1'].astype(str).str.strip().str.lower()
    tax_df_with_location['Region'] = tax_df_with_location['Location'].apply(get_region)
    
    region_stats = tax_df_with_location.groupby('Region').agg({
        'Phone_Number': 'count',
        'Response_Clean': lambda x: (x == 'registered').sum()
    }).reset_index()
    region_stats.columns = ['Region', 'Total_Invited', 'Registered']

    # Calculate positive responses by region
    positive_responses = tax_df_with_location[tax_df_with_location['Response_Clean'] == 'positive']
    if len(positive_responses) > 0:
        positive_by_region = positive_responses.groupby('Region').size().reset_index(name='Positive_Responses')
        region_stats = region_stats.merge(positive_by_region, on='Region', how='left')
    else:
        region_stats['Positive_Responses'] = 0

    region_stats['Positive_Responses'] = region_stats['Positive_Responses'].fillna(0).astype(int)

    # Calculate Total Confirmed = Registered + Positive
    region_stats['Total_Confirmed'] = region_stats['Registered'] + region_stats['Positive_Responses']
    region_stats['Unregistered'] = region_stats['Total_Invited'] - region_stats['Total_Confirmed']
    region_stats['Registration_Rate'] = (region_stats['Total_Confirmed'] / region_stats['Total_Invited'] * 100).round(2)
    
    # Filter out regions with 0 invited (empty regions)
    region_stats = region_stats[region_stats['Total_Confirmed'] > 0]
    
    # Sort by total for better visualization
    region_stats = region_stats.sort_values('Total_Confirmed', ascending=False)
    
    return html.Div([
        html.H4("Tax Contacts Analysis", className="mb-4"),
        
        dbc.Row([
            dbc.Col(create_summary_card("Total Invited", total, "envelope", "primary"), md=4),
            dbc.Col(create_summary_card("Total Registered", registered, "check-circle", "success"), md=4),
            dbc.Col(create_summary_card("Response Rate", 
                                       f"{round(tax_df['Response'].notna().sum()/total*100,2) if total>0 else 0}%", 
                                       "percentage", "info"), md=4),
        ], className="mb-4"),   
        
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Response Status Distribution"),
                    dbc.CardBody(dcc.Graph(figure=px.pie(values=responses.values, names=responses.index, hole=0.4)))
                ], className="shadow-sm")
            ], md=6),

            # NEW: Region-wise Analysis - Grouped Bar Chart    
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Region-wise Tax Contact Total Confirmations (Bar Chart)"),
                    dbc.CardBody(dcc.Graph(
                        figure=go.Figure(data=[
                            go.Bar(name='Total Confirmed', x=region_stats['Region'], y=region_stats['Total_Confirmed'], 
                                    marker_color='#9467bd', text=region_stats['Total_Confirmed'], textposition='auto',
                                    hovertemplate='<b>%{x}</b><br>Total Confirmed: %{y}<extra></extra>')
                        ]).update_layout(
                            barmode='group',
                            xaxis_title="Region",
                            yaxis_title="Count",
                            hovermode='x unified',
                            showlegend=True,
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                        )
                    ))
                ], className="shadow-sm")
            ], md=6),
        ], className="mb-4"),



        #    This section is commented out as per the new requirement it shows Registrations by Response separately it seems redundant as of now but if needed in future can be uncommented    
        #     dbc.Col([
        #         dbc.Card([
        #             dbc.CardHeader("Registrations by Response"),
        #             dbc.CardBody(dcc.Graph(figure=px.bar(responses.reset_index(), x='Response', y='Response_Weight')))
        #         ], className="shadow-sm")
        #     ], md=6),
        # ], className="mb-4"),       
        
        # Alternative: Line Chart for comparison
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Region-wise Tax Contact Total Confirmations (Line Chart)"),
                    dbc.CardBody(dcc.Graph(
                        figure=go.Figure(data=[
                            go.Scatter(name='Total Confirmed', x=region_stats['Region'], y=region_stats['Total_Confirmed'], 
                                    mode='lines+markers+text', marker=dict(size=10, color='#9467bd'),
                                    line=dict(width=3, color='#9467bd'),
                                    text=region_stats['Total_Confirmed'], textposition='top center',
                                    hovertemplate='<b>%{x}</b><br>Total Confirmed: %{y}<extra></extra>')
                        ]).update_layout(
                            xaxis_title="Region",
                            yaxis_title="Count",
                            hovermode='x unified',
                            showlegend=True,
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                        )
                    ))
                ], className="shadow-sm")
            ], md=12),
        ], className="mb-4"),
    
        # Optional: Add a stacked percentage view
        # Optional : Add a stacked percentage view which shows registration rate by region including unregistered and registered only for Tax contacts
        # dbc.Row([
        #     dbc.Col([
        #         dbc.Card([
        #             dbc.CardHeader("Registration Rate by Region"),
        #             dbc.CardBody(dcc.Graph(
        #                 figure=px.bar(region_stats, x='Region', y=['Registered', 'Unregistered'],
        #                             barmode='stack',
        #                             color_discrete_map={'Registered': '#2ca02c', 'Unregistered': '#d62728'},
        #                             labels={'value': 'Count', 'variable': 'Status'})
        #                 .update_traces(
        #                     text=region_stats[['Registered', 'Unregistered']].values.tolist(),
        #                     textposition='inside'
        #                 )
        #                 .update_layout(
        #                     xaxis_title="Region",
        #                     yaxis_title="Count",
        #                     showlegend=True
        #                 )
        #             ))
        #         ], className="shadow-sm")
        #     ], md=12),
        # ])
    ])
    

def create_cfo_tab(cfo_df):
    # To show where there is not output in CFO_tab
    if cfo_df.empty:
        return html.Div("No data available for current filters", className="text-muted text-center p-5")

    total = len(cfo_df)
    registered = len(cfo_df[cfo_df['Response_7'].str.lower() == 'registered'])
    responses = cfo_df.groupby('Response')['Response_Weight'].sum()
    
    # Region analysis for CFO contacts
    cfo_df_with_location = cfo_df[cfo_df['Location_6'].notna()].copy()
    cfo_df_with_location['Response_Clean'] = cfo_df_with_location['Response_7'].astype(str).str.strip().str.lower()
    cfo_df_with_location['Region'] = cfo_df_with_location['Location_6'].apply(get_region)
    
    region_stats = cfo_df_with_location.groupby('Region').agg({
        'Phone_Number_4': 'count',  # Total count
        'Response_Clean': lambda x: (x == 'registered').sum()  # Total registered (case-insensitive)
    }).reset_index()
    region_stats.columns = ['Region', 'Total_Invited', 'Registered']

    # Calculate positive responses by region
    positive_responses = cfo_df_with_location[cfo_df_with_location['Response_Clean'] == 'positive']
    if len(positive_responses) > 0:
        positive_by_region = positive_responses.groupby('Region').size().reset_index(name='Positive_Responses')
        region_stats = region_stats.merge(positive_by_region, on='Region', how='left')
    else:
        region_stats['Positive_Responses'] = 0

    region_stats['Positive_Responses'] = region_stats['Positive_Responses'].fillna(0).astype(int)

    # Calculate Total Confirmed = Registered + Positive
    region_stats['Total_Confirmed'] = region_stats['Registered'] + region_stats['Positive_Responses']
    region_stats['Unregistered'] = region_stats['Total_Invited'] - region_stats['Total_Confirmed']
    region_stats['Registration_Rate'] = (region_stats['Total_Confirmed'] / region_stats['Total_Invited'] * 100).round(2)

    # Filter out regions with 0 invited (empty regions)
    region_stats = region_stats[region_stats['Total_Confirmed'] > 0]

    region_stats = region_stats.sort_values('Total_Confirmed', ascending=False)
    
    return html.Div([
        html.H4("CFO Contacts Analysis", className="mb-4"),
        
        dbc.Row([
            dbc.Col(create_summary_card("Total Invited", total, "envelope", "primary"), md=4),
            dbc.Col(create_summary_card("Total Registered", registered, "check-circle", "success"), md=4),
            dbc.Col(create_summary_card("Response Rate", 
                                       f"{round(cfo_df['Response'].notna().sum()/total*100,2) if total>0 else 0}%", 
                                       "percentage", "info"), md=4),
        ], className="mb-4"),
        
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Response Status Distribution"),
                    dbc.CardBody(dcc.Graph(figure=px.pie(values=responses.values, names=responses.index, hole=0.4)))
                ], className="shadow-sm")
            ], md=6),

            # NEW: Region-wise Analysis for CFO - Grouped Bar Chart
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Region-wise CFO Contact Total Confirmations (Bar Chart)"),
                    dbc.CardBody(dcc.Graph(
                        figure=go.Figure(data=[
                            go.Bar(name='Total Confirmed', x=region_stats['Region'], y=region_stats['Total_Confirmed'], 
                                    marker_color='#9467bd', text=region_stats['Total_Confirmed'], textposition='auto',
                                    hovertemplate='<b>%{x}</b><br>Total Confirmed: %{y}<extra></extra>')
                        ]).update_layout(
                            barmode='group',
                            xaxis_title="Region",
                            yaxis_title="Count",
                            hovermode='x unified',
                            showlegend=True,
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                        )
                    ))
                ], className="shadow-sm")
            ], md=6),
        ], className="mb-4"),

            # This section is commented out as per the new requirement it shows Count of CFO by sector  separately it seems redundant as of now but if needed in future can be uncommented
            # dbc.Col([
            #     dbc.Card([
            #         dbc.CardHeader("CFO by Sector"),
            #         dbc.CardBody(dcc.Graph(figure=px.bar(cfo_df.groupby('Sector').size().reset_index(name='Count'), 
            #                                             x='Sector', y='Count')))
            #     ], className="shadow-sm")
            # ], md=6),
        # ], className="mb-4"),
        
                     
        
        # Alternative: Line Chart for comparison
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Region-wise CFO Contact Total Confirmations (Line Chart)"),
                    dbc.CardBody(dcc.Graph(
                        figure=go.Figure(data=[
                            go.Scatter(name='Total Confirmed', x=region_stats['Region'], y=region_stats['Total_Confirmed'], 
                                    mode='lines+markers+text', marker=dict(size=10, color='#9467bd'),
                                    line=dict(width=3, color='#9467bd'),
                                    text=region_stats['Total_Confirmed'], textposition='top center',
                                    hovertemplate='<b>%{x}</b><br>Total Confirmed: %{y}<extra></extra>')
                        ]).update_layout(
                            xaxis_title="Region",
                            yaxis_title="Count",
                            hovermode='x unified',
                            showlegend=True,
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                        )
                    ))
                ], className="shadow-sm")
            ], md=12),
        ], className="mb-4"),
    


        # Optionsl: Add a stacked percentage view
        #  Optional: Add a stacked percentage view which shows registration rate by region including unregistered and registered only for CFO contacts
        #  dbc.Row([
        #     dbc.Col([
        #         dbc.Card([
        #             dbc.CardHeader("Registration Rate by Region"),
        #             dbc.CardBody(dcc.Graph(
        #                 figure=px.bar(region_stats, x='Region', y=['Registered', 'Unregistered'],
        #                             barmode='stack',
        #                             color_discrete_map={'Registered': '#2ca02c', 'Unregistered': '#d62728'},
        #                             labels={'value': 'Count', 'variable': 'Status'})
        #                 .update_traces(
        #                     text=region_stats[['Registered', 'Unregistered']].values.tolist(),
        #                     textposition='inside'
        #                 )
        #                 .update_layout(
        #                     xaxis_title="Region",
        #                     yaxis_title="Count",
        #                     showlegend=True
        #                 )
        #             ))
        #         ], className="shadow-sm")
        #     ], md=12),
        # ])
    ])

def create_other_tab(other_df):
    # To show when there is no output in Others tab
    if other_df.empty:
        return html.Div("No data available for current filters", className="text-muted text-center p-5")

    total = len(other_df)
    registered = len(other_df[other_df['Response_13'].str.lower() == 'registered'])
    responses = other_df.groupby('Response')['Response_Weight'].sum()
    
    # Region analysis for Other contacts
    other_df_with_location = other_df[other_df['Location_12'].notna()].copy()
    other_df_with_location['Response_Clean'] = other_df_with_location['Response_13'].astype(str).str.strip().str.lower()
    other_df_with_location['Region'] = other_df_with_location['Location_12'].apply(get_region)
    
    region_stats = other_df_with_location.groupby('Region').agg({
    'Phone_Number_10': 'count',  # Total count
    'Response_Clean': lambda x: (x == 'registered').sum()  # Total registered (case-insensitive)
    }).reset_index()
    region_stats.columns = ['Region', 'Total_Invited', 'Registered']

    # Calculate positive responses by region
    positive_responses = other_df_with_location[other_df_with_location['Response_Clean'] == 'positive']
    if len(positive_responses) > 0:
        positive_by_region = positive_responses.groupby('Region').size().reset_index(name='Positive_Responses')
        region_stats = region_stats.merge(positive_by_region, on='Region', how='left')
    else:
        region_stats['Positive_Responses'] = 0

    region_stats['Positive_Responses'] = region_stats['Positive_Responses'].fillna(0).astype(int)

    # Calculate Total Confirmed = Registered + Positive
    region_stats['Total_Confirmed'] = region_stats['Registered'] + region_stats['Positive_Responses']
    region_stats['Unregistered'] = region_stats['Total_Invited'] - region_stats['Total_Confirmed']
    region_stats['Registration_Rate'] = (region_stats['Total_Confirmed'] / region_stats['Total_Invited'] * 100).round(2)

    # Filter out regions with 0 invited (empty regions)
    region_stats = region_stats[region_stats['Total_Confirmed'] > 0]

    region_stats = region_stats.sort_values('Total_Confirmed', ascending=False)
    
    return html.Div([
        html.H4("Other Contacts Analysis", className="mb-4"),
        
        dbc.Row([
            dbc.Col(create_summary_card("Total Invited", total, "envelope", "primary"), md=4),
            dbc.Col(create_summary_card("Total Registered", registered, "check-circle", "success"), md=4),
            dbc.Col(create_summary_card("Response Rate", 
                                       f"{round(other_df['Response'].notna().sum()/total*100,2) if total>0 else 0}%", 
                                       "percentage", "info"), md=4),
        ], className="mb-4"),
        
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Response Status Distribution"),
                    dbc.CardBody(dcc.Graph(figure=px.pie(values=responses.values, names=responses.index, hole=0.4)))
                ], className="shadow-sm")
            ], md=6),
        
        # NEW: Region-wise Analysis for Other contacts - Grouped Bar Chart
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Region-wise Other Contact Total Confirmations (Bar Chart)"),
                    dbc.CardBody(dcc.Graph(
                        figure=go.Figure(data=[
                            go.Bar(name='Total Confirmed', x=region_stats['Region'], y=region_stats['Total_Confirmed'], 
                                marker_color='#9467bd', text=region_stats['Total_Confirmed'], textposition='auto',
                                hovertemplate='<b>%{x}</b><br>Total Confirmed: %{y}<extra></extra>')
                        ]).update_layout(
                            barmode='group',
                            xaxis_title="Region",
                            yaxis_title="Count",
                            hovermode='x unified',
                            showlegend=True,
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                        )
                    ))
                ], className="shadow-sm")
            ], md=6),
        ], className="mb-4"),
        
        # Alternative: Line Chart for comparison
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Region-wise Other Contact Total Confirmations (Line Chart)"),
                    dbc.CardBody(dcc.Graph(
                        figure=go.Figure(data=[
                            go.Scatter(name='Total Confirmed', x=region_stats['Region'], y=region_stats['Total_Confirmed'], 
                                    mode='lines+markers+text', marker=dict(size=10, color='#9467bd'),
                                    line=dict(width=3, color='#9467bd'),
                                    text=region_stats['Total_Confirmed'], textposition='top center',
                                    hovertemplate='<b>%{x}</b><br>Total Confirmed: %{y}<extra></extra>')
                        ]).update_layout(
                            xaxis_title="Region",
                            yaxis_title="Count",
                            hovermode='x unified',
                            showlegend=True,
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                        )
                    ))
                ], className="shadow-sm")
            ], md=12),
        ], className="mb-4"),


        # # Optionsl: Add a stacked percentage view
        # Optional: Add a stacked percentage view which shows registration rate by region including unregistered and registered only for Other contacts
        # dbc.Row([
        #     dbc.Col([
        #         dbc.Card([
        #             dbc.CardHeader("Registration Rate by Region"),
        #             dbc.CardBody(dcc.Graph(
        #                 figure=px.bar(region_stats, x='Region', y=['Registered', 'Unregistered'],
        #                             barmode='stack',
        #                             color_discrete_map={'Registered': '#2ca02c', 'Unregistered': '#d62728'},
        #                             labels={'value': 'Count', 'variable': 'Status'})
        #                 .update_traces(
        #                     text=region_stats[['Registered', 'Unregistered']].values.tolist(),
        #                     textposition='inside'
        #                 )
        #                 .update_layout(
        #                     xaxis_title="Region",
        #                     yaxis_title="Count",
        #                     showlegend=True
        #                 )
        #             ))
        #         ], className="shadow-sm")
        #     ], md=12),
        # ])
    ])

def create_metrics_tab(df):
    # To show when there is no output in the metrics tab
    if df.empty:
        return html.Div("No data available for current filters", className="text-muted text-center p-5")
    
    total_invitees = df['numInvitees'].apply(safe_int).sum()
    total_reg = df['numRegistrations'].apply(safe_int).sum()
    conversion_rate = calculate_conversion_rate(total_reg, total_invitees)
    response_rate = round((df['Response'].notna().sum() / len(df) * 100), 2) if len(df) > 0 else 0
    pending_followups = len(df[df['Response'].isna()])
    
    # Circle back analysis
    circle_back_df = df[df['Circle_Back_Dt'].notna()]
    
    # Trend analysis by date
    if 'Invite_Dt' in df.columns:
        df['Invite_Dt_parsed'] = pd.to_datetime(df['Invite_Dt'], errors='coerce')
        invite_trend = df.groupby(df['Invite_Dt_parsed'].dt.date).size().reset_index(name='Count')
        invite_trend.columns = ['Date', 'Invites']
    else:
        invite_trend = pd.DataFrame()
    
    return html.Div([
        html.H4("Key Metrics & Performance", className="mb-4"),
        
        dbc.Row([
            dbc.Col(create_summary_card("Conversion Rate", f"{conversion_rate}%", "chart-line", "success"), md=3),
            dbc.Col(create_summary_card("Response Rate", f"{response_rate}%", "percentage", "info"), md=3),
            dbc.Col(create_summary_card("Pending Follow-ups", pending_followups, "clock", "warning"), md=3),
            dbc.Col(create_summary_card("Circle Backs", len(circle_back_df), "redo", "danger"), md=3),
        ], className="mb-4"),
        
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Invite Trend Over Time"),
                    dbc.CardBody(dcc.Graph(
                        figure=px.line(invite_trend, x='Date', y='Invites', 
                                      title="Daily Invite Distribution") if not invite_trend.empty 
                        else go.Figure().add_annotation(text="No date data available", showarrow=False)
                    ))
                ], className="shadow-sm")
            ], md=12),
        ], className="mb-4"),
        
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Conversion Funnel"),
                    dbc.CardBody(dcc.Graph(
                        figure=go.Figure(go.Funnel(
                            y=['Total Clients', 'Total Invitees', 'Responses', 'Registrations'],
                            x=[len(df), total_invitees, df['Response'].notna().sum(), total_reg],
                            textinfo="value+percent initial"
                        ))
                    ))
                ], className="shadow-sm")
            ], md=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Response Status Breakdown"),
                    dbc.CardBody(dcc.Graph(
                        figure=px.bar(
                            df.groupby('Response')['Response_Weight'].sum().reset_index(),
                            x='Response', y='Response_Weight',
                            color='Response',
                            title="Response Distribution"
                        )
                    ))
                ], className="shadow-sm")
            ], md=6),
        ])
    ])



# This section is commented out as data table exports are not needed as of now uncomment to use it
'''  .
# Export callbacks
@app.callback(
    Output("ph-table-download", "data"),
    Input("ph-table-export", "n_clicks"),
    State("ph-table", "data"),
    prevent_initial_call=True
)
def export_ph_table(n_clicks, data):
    if n_clicks:
        df = pd.DataFrame(data)
        return dcc.send_data_frame(df.to_excel, "practice_head_data.xlsx", index=False)

@app.callback(
    Output("partner-table-download", "data"),
    Input("partner-table-export", "n_clicks"),
    State("partner-table", "data"),
    prevent_initial_call=True
)
def export_partner_table(n_clicks, data):
    if n_clicks:
        df = pd.DataFrame(data)
        return dcc.send_data_frame(df.to_excel, "partner_data.xlsx", index=False)

@app.callback(
    Output("tax-detail-table-download", "data"),
    Input("tax-detail-table-export", "n_clicks"),
    State("tax-detail-table", "data"),
    prevent_initial_call=True
)
def export_tax_table(n_clicks, data):
    if n_clicks:
        df = pd.DataFrame(data)
        return dcc.send_data_frame(df.to_excel, "tax_contacts_data.xlsx", index=False)

@app.callback(
    Output("cfo-detail-table-download", "data"),
    Input("cfo-detail-table-export", "n_clicks"),
    State("cfo-detail-table", "data"),
    prevent_initial_call=True
)
def export_cfo_table(n_clicks, data):
    if n_clicks:
        df = pd.DataFrame(data)
        return dcc.send_data_frame(df.to_excel, "cfo_contacts_data.xlsx", index=False)

@app.callback(
    Output("other-detail-table-download", "data"),
    Input("other-detail-table-export", "n_clicks"),
    State("other-detail-table", "data"),
    prevent_initial_call=True
)
def export_other_table(n_clicks, data):
    if n_clicks:
        df = pd.DataFrame(data)
        return dcc.send_data_frame(df.to_excel, "other_contacts_data.xlsx", index=False)
'''
        
@app.server.route('/health')
def health_check():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM tax_summit_master_data")
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return f"OK - {count} records in master table"
    return "ERROR - Cannot connect to database", 500

if __name__ == '__main__':
    port = int(os.getenv("PORT", 8050))
    app.run(debug=False, host='0.0.0.0', port=port)  