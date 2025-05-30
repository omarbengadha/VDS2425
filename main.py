import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import os
import glob

DATA_DIR = "VDS2425_Madrid"  # Directory containing Madrid data CSVs

# Use of browser for interactive viewing
pio.renderers.default = "browser"


def seasonal_pollution_chart():
    """
    Reads pollution CSVs (2001–2018), computes seasonal averages per pollutant,
    ranks seasons within each year, and returns a Plotly grouped bar chart with a dropdown.
    """
    file_pattern = os.path.join(DATA_DIR, "madrid_*.csv")
    files = sorted(glob.glob(file_pattern))
    if not files:
        raise FileNotFoundError(f"No CSV files found at: {file_pattern}")

    df_list = []
    for f in files:
        df = pd.read_csv(f, parse_dates=['date'])
        df['year'] = df['date'].dt.year
        df['month'] = df['date'].dt.month
        df['season'] = df['month'].map(lambda m:
                                       'Winter' if m in [12, 1, 2] else
                                       'Spring' if m in [3, 4, 5] else
                                       'Summer' if m in [6, 7, 8] else 'Fall')

        id_vars = ['year', 'season']
        value_vars = [c for c in df.columns if c not in [
            'date', 'station_id', 'month', 'year', 'season']]
        df_melt = df.melt(id_vars=id_vars, value_vars=value_vars,
                          var_name='pollutant', value_name='value')
        df_melt = df_melt.dropna(subset=['value'])
        df_list.append(df_melt)

    data = pd.concat(df_list, ignore_index=True)

    data_avg = data.groupby(['year', 'season', 'pollutant'], as_index=False).agg(
        avg_value=('value', 'mean'))
    data_avg['rank'] = data_avg.groupby(['year', 'pollutant'])[
        'avg_value'].rank(ascending=False, method='dense')

    pollutants = sorted(data_avg['pollutant'].unique())
    seasons = ['Winter', 'Spring', 'Summer', 'Fall']
    fig = go.Figure()

    for pollutant in pollutants:
        df_p = data_avg[data_avg['pollutant'] == pollutant]
        for season in seasons:
            df_ps = df_p[df_p['season'] == season]
            fig.add_trace(go.Bar(
                x=df_ps['year'].astype(str),
                y=df_ps['avg_value'],
                name=season,
                customdata=df_ps[['rank']].values,
                text=df_ps['rank'].astype(int),
                textposition='outside',
                visible=(pollutant == 'NO_2'),
                hovertemplate='Year: %{x}<br>' +
                              f'Season: {season}<br>' +
                              'Avg: %{y:.1f} µg/m³<br>' +
                              'Rank: %{customdata[0]:.0f}<extra></extra>'
            ))

    buttons = []
    for i, pollutant in enumerate(pollutants):
        visible = [(pollutants[j] == pollutant)
                   for j in range(len(pollutants)) for _ in seasons]
        buttons.append(dict(
            label=pollutant,
            method='update',
            args=[{'visible': visible},
                  {'title': f'Seasonal Pollution Levels by Year: {pollutant}'}]
        ))

    fig.update_layout(
        updatemenus=[dict(active=pollutants.index(
            'NO_2'), buttons=buttons, x=1.1, y=1)],
        barmode='group',
        title='Yearly Seasonal Pollution Levels: NO_2',
        xaxis_title='Year',
        yaxis_title='Avg Concentration (µg/m³)',
        legend_title='Season'
    )

    fig.write_html("BA2_seasonal_bar_chart.html", auto_open=True)
    return fig


def seasonal_pollution_pie_chart(pollutant='NO_2'):
    """
    Computes the overall seasonal average of a pollutant from 2001 to 2018,
    and returns a Plotly pie chart showing percentage share per season.
    """
    file_pattern = os.path.join(DATA_DIR, "madrid_*.csv")
    df_list = []
    for path in sorted(glob.glob(file_pattern)):
        df = pd.read_csv(path, parse_dates=['date'])
        if pollutant not in df.columns:
            print(
                f"⚠️ Pollutant '{pollutant}' not found in {path}. Skipping...")
            continue
        df['month'] = df['date'].dt.month
        df['season'] = df['month'].map(lambda m:
                                       'Winter' if m in (12, 1, 2) else
                                       'Spring' if m in (3, 4, 5) else
                                       'Summer' if m in (6, 7, 8) else 'Fall')
        df_list.append(df[['season', pollutant]].dropna())

    if not df_list:
        raise ValueError(f"No data found for pollutant '{pollutant}'")

    all_data = pd.concat(df_list, ignore_index=True)

    season_means = all_data.groupby('season', as_index=False)[pollutant].mean(
    ).set_index('season').reindex(['Winter', 'Spring', 'Summer', 'Fall'])
    season_means['percent'] = season_means[pollutant] / \
        season_means[pollutant].sum()

    fig = go.Figure(data=go.Pie(
        labels=season_means.index,
        values=season_means['percent'],
        sort=False,
        marker_colors=['#1f77b4', '#d62728', '#2ca02c', '#9467bd'],
        textposition='outside',
        outsidetextfont=dict(size=18),
        hoverinfo='label+percent+value',
        hovertemplate=(
            "%{label}<br>"
            + pollutant + ": %{value:.1%}<br>"
            + "Avg: %{customdata:.1f} µg/m³<extra></extra>"
        ),
        customdata=season_means[pollutant].values,
        textinfo='label+percent'
    ))

    fig.update_layout(
        title=f"Overall Seasonal Pollution Average ({pollutant}, 2001–2018)",
        legend=dict(traceorder='normal')
    )

    fig.write_html("BA2_seasonal_pie_chart.html", auto_open=True)
    return fig


def station_ranking_chart():
    """
    Builds an interactive horizontal bar chart showing 2018 average pollution levels
    for each station in Madrid, with dropdown to switch among NO, NO₂, and NOx.
    """
    POLLUTION_2018 = os.path.join(DATA_DIR, "madrid_2018.csv")
    STATIONS_FILE = os.path.join(DATA_DIR, "stations.csv")
    pollution_data = pd.read_csv(POLLUTION_2018)
    station_info = pd.read_csv(STATIONS_FILE)

    selected_pollutants = ["NO", "NO_2", "NOx"]

    pollutant_avgs = (
        pollution_data
        .groupby("station")[selected_pollutants]
        .mean()
        .reset_index()
        .merge(station_info, left_on="station", right_on="id", how="left")
    )

    pollutant_avgs["name"] = pollutant_avgs["name"].fillna(
        pollutant_avgs["station"].astype(str))

    fig = go.Figure()

    for pollutant in selected_pollutants:
        df_sorted = (
            pollutant_avgs[["name", pollutant]]
            .dropna()
            .sort_values(by=pollutant, ascending=False)
        )

        colors = [
            'blue' if val < 20 else
            'orange' if val < 40 else
            'red'
            for val in df_sorted[pollutant]
        ]

        fig.add_trace(go.Bar(
            x=df_sorted[pollutant],
            y=df_sorted["name"],
            orientation='h',
            marker=dict(color=colors),
            text=[f"{name}<br>{pollutant}: {val:.1f} µg/m³"
                  for name, val in zip(df_sorted["name"], df_sorted[pollutant])],
            hoverinfo='text',
            showlegend=False,
            visible=(pollutant == "NO_2")
        ))

    # Add dummy traces for pollution tiers
    fig.add_trace(go.Bar(x=[None], y=[None], marker=dict(
        color='red'), name='High pollution'))
    fig.add_trace(go.Bar(x=[None], y=[None], marker=dict(
        color='orange'), name='Medium pollution'))
    fig.add_trace(go.Bar(x=[None], y=[None], marker=dict(
        color='blue'), name='Low pollution'))

    buttons = []
    for i, pollutant in enumerate(selected_pollutants):
        visibility = [False] * len(selected_pollutants) + [True] * 3
        visibility[i] = True
        buttons.append(dict(
            label=pollutant,
            method="update",
            args=[{"visible": visibility},
                  {"title": f"Average {pollutant} Pollution by Station (2018)",
                   "xaxis": {"title": f"Average {pollutant} Concentration (µg/m³)"},
                   "yaxis": {"title": "Station"}}]
        ))

    fig.update_layout(
        updatemenus=[dict(
            active=selected_pollutants.index("NO_2"),
            buttons=buttons,
            x=1.1, y=1.1,
            showactive=True
        )],
        legend_title_text="Pollution Level Tier",
        title="Average NO₂ Pollution by Station (2018)",
        xaxis_title="Average NO₂ Concentration (µg/m³)",
        yaxis_title="Station",
        height=700
    )

    fig.update_yaxes(autorange="reversed")
    fig.write_html("BCK2_station_pollution_chart.html", auto_open=True)
    return fig


def pollution_trend_chart():
    """
    Creates an interactive multi-line chart showing annual average pollution levels
    for NO₂, PM10, and O₃ between 2001 and 2018, enabling spike/drop detection.
    """

    df = pd.read_csv("annual_pollution_2001_2018.csv")
    pollutants = ['NO_2', 'PM10', 'O_3']
    colors = ['red', 'blue', 'green']

    # Calculate yearly change (optional)
    for pol in pollutants:
        df[f'delta_{pol}'] = df[pol].diff()

    fig = go.Figure()

    for i, pol in enumerate(pollutants):
        fig.add_trace(go.Scatter(
            x=df['year'],
            y=df[pol],
            mode='lines+markers',
            name=pol,
            line=dict(color=colors[i]),
            hovertemplate=f"<b>{pol}</b><br>Year: %{{x}}<br>Avg: %{{y:.2f}} µg/m³<extra></extra>"
        ))

    fig.update_layout(
        title=dict(
            text="OMR_4: Pollution Spike and Drop Line Chart (2001–2018)",
            font=dict(size=20)
        ),
        xaxis=dict(
            title=dict(text="Year", font=dict(size=16)),
            tickmode='linear',
            dtick=1,
            showgrid=True,
            gridcolor='lightgray',
            tickfont=dict(size=14)
        ),
        yaxis=dict(
            title=dict(text="Average Pollution (µg/m³)", font=dict(size=16)),
            showgrid=True,
            gridcolor='lightgray',
            tickfont=dict(size=14)
        ),
        legend=dict(
            font=dict(size=14),
            title=dict(text="Pollutant", font=dict(size=15))
        ),
        template="plotly_white",
        font=dict(size=14)
    )

    fig.write_html("OMR4_pollution_trend.html", auto_open=True)
    return fig


if __name__ == "__main__":
    seasonal_pollution_pie_chart()
    seasonal_pollution_chart()
    station_ranking_chart()
    pollution_trend_chart()
