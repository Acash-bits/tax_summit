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
        port = int(os.getenv("DB_PORT", 3306))
        return mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            database=os.getenv("DB_NAME"),
            port = port
        )
    except Error as e:
        print(f"Error: {e}")
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
    
    tax_df = pd.read_sql("SELECT * FROM Tax_Persons_Analysis", conn)
    cfo_df = pd.read_sql("SELECT * FROM CFO_Persons_Analysis", conn)
    other_df = pd.read_sql("SELECT * FROM Other_Persons_Analysis", conn)
    conn.close()
    
    return tax_df, cfo_df, other_df

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

def create_data_table(df, table_id):
    if df.empty:
        return html.Div("No data available", className="text-muted text-center p-4")
    
    return html.Div([
        dbc.Row([
            dbc.Col(html.H6([html.I(className="fas fa-table me-2"), "Detailed Data"], className="mb-3"), md=9),
            dbc.Col(dbc.Button([html.I(className="fas fa-file-excel me-2"), "Export"], 
                              id=f"{table_id}-export", color="success", size="sm", className="w-100"), md=3)
        ]),
        dash_table.DataTable(
            id=table_id,
            columns=[{"name": i, "id": i} for i in df.columns],
            data=df.to_dict('records'),
            page_size=10,
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'left', 'padding': '8px', 'fontSize': '12px'},
            style_header={'backgroundColor': '#2c3e50', 'color': 'white', 'fontWeight': 'bold'},
            style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#f8f9fa'}],
            filter_action="native",
            sort_action="native",
            sort_mode="multi"
        ),
        dcc.Download(id=f"{table_id}-download")
    ], className="mt-4")

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
    
    if master_df.empty:
        return [], [], [], [], [], {}, {}, {}, {}
    
    ph_opts = [{'label': x, 'value': x} for x in master_df['Practice_Head'].dropna().unique()]
    partner_opts = [{'label': x, 'value': x} for x in master_df['Partner'].dropna().unique()]
    sector_opts = [{'label': x, 'value': x} for x in master_df['Sector'].dropna().unique()]
    loc_opts = [{'label': x, 'value': x} for x in master_df['Location'].dropna().unique()]
    resp_opts = [{'label': x, 'value': x} for x in master_df['Response'].dropna().unique()]
    
    return (ph_opts, partner_opts, sector_opts, loc_opts, resp_opts, 
            master_df.to_dict('records'), tax_df.to_dict('records'), 
            cfo_df.to_dict('records'), other_df.to_dict('records'))

@app.callback(
    Output('filtered-data', 'data'),
    [Input('apply-filters', 'n_clicks'), Input('reset-filters', 'n_clicks')],
    [State('master-data', 'data'), State('practice-head-filter', 'value'),
     State('partner-filter', 'value'), State('sector-filter', 'value'),
     State('location-filter', 'value'), State('response-filter', 'value')]
)
def filter_data(apply, reset, data, ph, partner, sector, loc, resp):
    ctx = callback_context
    if not data:
        return {}
    
    df = pd.DataFrame(data)
    
    if ctx.triggered and 'reset' in ctx.triggered[0]['prop_id']:
        return df.to_dict('records')
    
    if ph:
        df = df[df['Practice_Head'].isin(ph)]
    if partner:
        df = df[df['Partner'].isin(partner)]
    if sector:
        df = df[df['Sector'].isin(sector)]
    if loc:
        df = df[df['Location'].isin(loc)]
    if resp:
        df = df[df['Response'].isin(resp)]
    
    return df.to_dict('records')

@app.callback(
    Output('tab-content', 'children'),
    [Input('tabs', 'active_tab'), Input('filtered-data', 'data'),
     Input('tax-data', 'data'), Input('cfo-data', 'data'), Input('other-data', 'data')]
)
def render_content(tab, filtered, tax, cfo, other):
    if not filtered:
        return html.Div("Loading...", className="text-center p-5")
    
    df = pd.DataFrame(filtered)
    tax_df = pd.DataFrame(tax)
    cfo_df = pd.DataFrame(cfo)
    other_df = pd.DataFrame(other)
    
    if tab == "overview":
        return create_overview_tab(df)
    elif tab == "practice-head":
        return create_practice_head_tab(df, tax_df, cfo_df, other_df)
    elif tab == "partner":
        return create_partner_tab(df, tax_df, cfo_df, other_df)
    elif tab == "tax":
        return create_tax_tab(tax_df)
    elif tab == "cfo":
        return create_cfo_tab(cfo_df)
    elif tab == "other":
        return create_other_tab(other_df)
    elif tab == "metrics":
        return create_metrics_tab(df)

def create_overview_tab(df):
    total_invites = len(df)
    total_invitees = df['numInvitees'].apply(safe_int).sum()
    total_reg = df['numRegistrations'].apply(safe_int).sum()
    resp_rate = round((df['Response'].notna().sum() / len(df) * 100), 2) if len(df) > 0 else 0
    
    resp_dist = df['Response'].value_counts()
    
    sector_perf = df.groupby('Sector').agg({
        'numInvitees': lambda x: x.apply(safe_int).sum(),
        'numRegistrations': lambda x: x.apply(safe_int).sum()
    }).reset_index()
    sector_perf['Conversion'] = sector_perf.apply(
        lambda r: calculate_conversion_rate(r['numRegistrations'], r['numInvitees']), axis=1
    )
    
    return html.Div([
        dbc.Row([
            dbc.Col(create_summary_card("Total Invites", f"{total_invites:,}", "envelope", "primary"), md=3),
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
            ], md=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Sector Performance"),
                    dbc.CardBody(dcc.Graph(figure=px.bar(sector_perf, x='Sector', y='Conversion', 
                                                        color='Conversion', color_continuous_scale='Viridis')))
                ], className="shadow-sm")
            ], md=6),
        ])
    ])

def create_practice_head_tab(df, tax_df, cfo_df, other_df):
    # Group by Practice Head
    ph_stats = df.groupby('Practice_Head').agg({
        'Client_Name': 'count',
        'numInvitees': lambda x: x.apply(safe_int).sum(),
        'numRegistrations': lambda x: x.apply(safe_int).sum(),
        'Response': lambda x: x.notna().sum()
    }).reset_index()
    ph_stats.columns = ['Practice_Head', 'Invites_Sent', 'Invitees', 'Registrations', 'Responses']
    
    response_by_ph = df.groupby(['Practice_Head', 'Response']).size().reset_index(name='Count')
    sector_by_ph = df.groupby(['Practice_Head', 'Sector']).size().reset_index(name='Count')
    location_by_ph = df.groupby(['Practice_Head', 'Location']).size().reset_index(name='Count')
    
    tax_by_ph = tax_df.groupby(['Practice_Head', 'Response']).size().reset_index(name='Count')
    cfo_by_ph = cfo_df.groupby(['Practice_Head', 'Response']).size().reset_index(name='Count')
    other_by_ph = other_df.groupby(['Practice_Head', 'Response']).size().reset_index(name='Count')
    
    return html.Div([
        html.H4("Practice Head Analysis", className="mb-4"),
        
        dbc.Row([
            dbc.Col(create_summary_card("Total Invites", ph_stats['Invites_Sent'].sum(), "paper-plane", "primary"), md=3),
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
        
        create_data_table(ph_stats, "ph-table")
    ])

def create_partner_tab(df, tax_df, cfo_df, other_df):
    partner_stats = df.groupby('Partner').agg({
        'Client_Name': 'count',
        'numInvitees': lambda x: x.apply(safe_int).sum(),
        'numRegistrations': lambda x: x.apply(safe_int).sum(),
        'Response': lambda x: x.notna().sum()
    }).reset_index()
    partner_stats.columns = ['Partner', 'Invites_Sent', 'Invitees', 'Registrations', 'Responses']
    
    response_by_partner = df.groupby(['Partner', 'Response']).size().reset_index(name='Count')
    location_by_partner = df.groupby(['Partner', 'Location']).size().reset_index(name='Count')
    
    tax_by_partner = tax_df.groupby(['Partner', 'Response']).size().reset_index(name='Count')
    cfo_by_partner = cfo_df.groupby(['Partner', 'Response']).size().reset_index(name='Count')
    other_by_partner = other_df.groupby(['Partner', 'Response']).size().reset_index(name='Count')
    
    return html.Div([
        html.H4("Partner Analysis", className="mb-4"),
        
        dbc.Row([
            dbc.Col(create_summary_card("Total Invites", partner_stats['Invites_Sent'].sum(), "paper-plane", "primary"), md=3),
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
        
        create_data_table(partner_stats, "partner-table")
    ])

def create_tax_tab(tax_df):
    total = len(tax_df)
    registered = tax_df['numRegistrations'].apply(safe_int).sum()
    responses = tax_df['Response'].value_counts()
    
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
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Registrations by Response"),
                    dbc.CardBody(dcc.Graph(figure=px.bar(responses.reset_index(), x='Response', y='count')))
                ], className="shadow-sm")
            ], md=6),
        ], className="mb-4"),
        
        create_data_table(tax_df, "tax-detail-table")
    ])

def create_cfo_tab(cfo_df):
    total = len(cfo_df)
    registered = cfo_df['numRegistrations'].apply(safe_int).sum()
    responses = cfo_df['Response'].value_counts()
    
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
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("CFO by Sector"),
                    dbc.CardBody(dcc.Graph(figure=px.bar(cfo_df.groupby('Sector').size().reset_index(name='Count'), 
                                                        x='Sector', y='Count')))
                ], className="shadow-sm")
            ], md=6),
        ], className="mb-4"),
        
        create_data_table(cfo_df, "cfo-detail-table")
    ])

def create_other_tab(other_df):
    total = len(other_df)
    registered = other_df['numRegistrations'].apply(safe_int).sum()
    responses = other_df['Response'].value_counts()
    
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
            ], md=12),
        ], className="mb-4"),
        
        create_data_table(other_df, "other-detail-table")
    ])

def create_metrics_tab(df):
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
                            y=['Total Invites', 'Total Invitees', 'Responses', 'Registrations'],
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
                            df['Response'].value_counts().reset_index(),
                            x='Response', y='count',
                            color='Response',
                            title="Response Distribution"
                        )
                    ))
                ], className="shadow-sm")
            ], md=6),
        ])
    ])

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

if __name__ == '__main__':
    port = int(os.getenv("PORT", 8050))
    app.run(debug=False, host='0.0.0.0', port=port)  