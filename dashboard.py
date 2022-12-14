import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output
import numpy as np
from heapq import heapify, heappush, heappop
import random


def change_data_format(df):
    start_year, end_year = df['Year'].min(), df['Year'].max()
    df = df.sort_values(by='Country')
    data = list()
    prev_country = ''
    data_row = list()
    for index, row in df.iterrows():
        if prev_country != row.Country:
            if len(data_row):
                v = np.array(data_row[1:])
                mi, ma = v.min(), v.max()
                if mi != ma:
                    v = (v - mi) / (ma - mi)
                data_row = data_row[:1] + v.tolist()
                data.append(data_row)
            data_row = list()
            data_row.append(row['Country'])
            prev_country = row['Country']
        data_row.append(row['Total'])
    if len(data_row):
        data.append(data_row)
    columns = ['Country']
    for year in range(start_year, end_year + 1):
        columns.append(str(year))
    df = pd.DataFrame(data, columns=columns)
    df = df.fillna(0)
    # print(df.head())
    return df


def dtw(a, b):
    a = np.array(a)
    b = np.array(b)

    c = np.zeros((len(a), len(b)))
    c[0][0] = abs(a[0] - b[0])
    n = len(a)

    for i in range(1, n):
        c[0][i] = c[0][i - 1] + abs(b[0] - a[i])

    for i in range(1, n):
        c[i][0] = c[i - 1][0] + abs(b[i] - a[0])

    for i in range(1, n):
        for j in range(1, n):
            c[i][j] = abs(b[i] - a[j])
            c[i][j] += min([c[i - 1][j - 1], c[i][j - 1], c[i - 1][j]])

    return c[-1][-1]


def euclidean_distance(a,b):
    a = np.array(a)
    b = np.array(b)

    distance = np.sqrt(np.sum(np.square(a - b)))
    return(distance)


def create_proximity_matrix(df, distance):
    countries = sorted(list(set(df['Country'].tolist())))
    cnty_index = dict()
    for i, country in enumerate(countries):
        cnty_index[country] = i

    df = df.sort_values(by=['Country'])
    n = len(countries)
    prox_mat = np.zeros((n, n))

    for index, row in df.iterrows():
        for index2, row2 in df[index + 1:].iterrows():
            if distance == 'DTW':
                value = dtw(row.tolist()[1:], row2.tolist()[1:])
            else:
                value = euclidean_distance(row.tolist()[1:], row2.tolist()[1:])
            index1 = cnty_index[row['Country']]
            index2 = cnty_index[row2['Country']]
            prox_mat[index1][index2] = value
            prox_mat[index2][index1] = value

    return prox_mat, cnty_index


def merge(clusters, prox_mat, inter_distance):
    cluster_keys = sorted(list(clusters.keys()))
    merge_cluster = (cluster_keys[0], cluster_keys[1])
    distance = prox_mat[merge_cluster[0]][merge_cluster[1]]

    for i, key1 in enumerate(cluster_keys):
        for key2 in cluster_keys[i+1:]:
            for series1 in clusters[key1]:
                for series2 in clusters[key2]:
                    new_distance = prox_mat[series1][series2]
                    if inter_distance == "MIN" and new_distance < distance:
                        distance = new_distance
                        merge_cluster = (key1, key2)
                    elif inter_distance == 'MAX' and new_distance > distance:
                        distance = new_distance
                        merge_cluster = (key1, key2)

    return merge_cluster

def merge_queue(clusters, prox_mat, inter_distance):
    heap = []
    heapify(heap)
    cluster_keys = sorted(list(clusters.keys()))
    merge_cluster = (cluster_keys[0], cluster_keys[1])
    distance = prox_mat[merge_cluster[0]][merge_cluster[1]]

    for i, key1 in enumerate(cluster_keys):
        for key2 in cluster_keys[i+1:]:
            for series1 in clusters[key1]:
                for series2 in clusters[key2]:
                    new_distance = prox_mat[series1][series2]
                    # if inter_distance == "MIN" and new_distance < distance:
                    #     distance = new_distance
                    #     merge_cluster = (key1, key2)
                    # elif inter_distance == 'MAX' and new_distance > distance:
                    #     distance = new_distance
                    #     merge_cluster = (key1, key2)
                    if inter_distance == 'MIN':
                        heappush(heap, [new_distance, series1, series2])
                    elif inter_distance == 'MAX':
                        heappush(heap, [-new_distance, series1, series2])

    return heap


def create_hierarchical_clusters(prox_mat, cnty_ind, k, inter_cluster):
    clusters = dict()
    series_cluster = dict()
    n = len(prox_mat)
    for i in range(n):
        clusters[i] = {i}
        series_cluster[i] = i

    heap = merge_queue(clusters, prox_mat, inter_cluster)
    # heapify(heap)
    while len(clusters.keys()) > k:
        # c1, c2 = merge(clusters, prox_mat, inter_cluster)

        a, c1, c2 = heappop(heap)
        while series_cluster[c1] == series_cluster[c2]:
            a, c1, c2 = heappop(heap)

        c1 = series_cluster[c1]
        c2 = series_cluster[c2]
        new_cluster = clusters[c1].union(clusters[c2])
        del clusters[c1]
        del clusters[c2]
        clusters[c1] = new_cluster
        for c in new_cluster:
            series_cluster[c] = c1

        # print(clusters)

    data = dict()
    for key, values in clusters.items():
        value = list(values)
        for val in value:
            data[val] = key

    ind_cnt = ['0'] * len(cnty_ind.keys())
    for key, value in sorted(cnty_ind.items(), key=lambda x: x[0]):
        ind_cnt[value] = key

    data = [[ind_cnt[key], value] for key, value in data.items()]
    columns = ['Country', 'Cluster']
    new_df = pd.DataFrame(data, columns=columns)
    return new_df


def change_cluster_index(df):
    clusters = list(set(df['Cluster'].tolist()))
    mapping = dict()
    for i, cluster in enumerate(clusters):
        mapping[cluster] = i
    new_cluster = []
    for index, row in df.iterrows():
        new_cluster.append(mapping[row['Cluster']])

    df = df.drop(['Cluster'], axis=1)
    df['Cluster'] = new_cluster
    return df


def choose_n_random(df, n):
    return df.sample(min(n, len(df)))


# -- creating dictionaries
dfs = {
    'CO2': 'co2.csv',
    'Climate': 'climate.csv',
    'expenditure': 'expenditure.csv',
    'temperature': 'temperature.csv'
}
df = pd.read_csv('climate.csv')
label = {
    'co2.csv': 'CO2 Emission',
    'climate.csv': 'Number of climate related Disasters',
    'expenditure.csv': 'Expenditure in the domestic currency',
    'temperature.csv': 'Temperature change with respect to a baseline climatology'
}

# ------------------------------------------------------------------------------
app = Dash(__name__)

# App layout
app.layout = html.Div([

    html.H1("Climate Change Dashboard", style={'text-align': 'center'}),

    html.Div(style={"flex": "1"}, children=[
                html.H4('Select Dataset'),
                dcc.Dropdown(id="dataset",
                             options=[{'label': key, 'value': value} for key, value in dfs.items()],
                             multi=False,
                             style={'width': "100%"},
                             value=dfs['Climate']
                             ),
            ]),

    dcc.Graph(id='my_bee_map', figure={}),

    html.Div(style={"display": "flex", 'margin': "auto", "text-align": "center"}, children=[
        html.Div(style={"flex": "1"}, children=[
            html.H4('Select value of K'),
            dcc.Dropdown(id="k_value",
                                 options=[{'label': k, 'value': k} for k in range(1, 2, len(set(df.Country.tolist()))+1)],
                                 multi=False,
                                 style={'width': "100%"},
                                 value=6
                             ),

        ]),
        html.Div(style={"flex": "1"}, children=[
                    html.H4('Distance Metric'),
                    dcc.Dropdown(id="distance",
                                         options=[{'label': 'DTW', 'value': 'DTW'}, {'label': 'Euclidean', 'value': 'Euclidean'} ],
                                         multi=False,
                                         style={'width': "100%"},
                                         value='DTW'
                                     ),

                ]),
        html.Div(style={"flex": "1"}, children=[
                    html.H4('Inter Cluster Similarity'),
                    dcc.Dropdown(id="inter_cluster",
                                         options=[{'label': 'MIN', 'value': 'MIN'},
                                                  {'label': 'MAX', 'value' : 'MAX'}
                                                  ],
                                         multi=False,
                                         style={'width': "100%"},
                                         value='MIN'
                                     ),

                ]),
    ]),

    dcc.Graph(id='my_bee_map2', figure={}),
])


# ------------------------------------------------------------------------------
# Connect the Plotly graphs with Dash Components
@app.callback(
    [
        Output(component_id='my_bee_map', component_property='figure'),
     ],
    [
        Input(component_id='dataset', component_property='value'),
        # Input(component_id='k_value', component_property='value'),
        # Input(component_id='distance', component_property='value'),
        # Input(component_id='inter_cluster', component_property='value'),
    ]
)
def update1(dataset):
    df = pd.read_csv(str(dataset))                      # reading data
    df = change_data_format(df)
    # df = choose_n_random(df, 300)
    prox_mat, cnty_index = create_proximity_matrix(df, 'DTW')
    dff = create_hierarchical_clusters(prox_mat, cnty_index, k=random.randint(50, 80), inter_cluster='MIN')
    dff = change_cluster_index(dff)
    fig = px.choropleth(dff,
                        locationmode='country names',
                        locations="Country",
                        color="Cluster",  # lifeExp is a column of gapminder
                        hover_name="Country",  # column to add to hover information
                        color_continuous_scale=px.colors.sequential.Turbo
                        # labels={'Cluster': label[dataset]}
    )
    print('computations for the first graph is completed')
    return [fig]

const_df = pd.read_csv('temperature.csv')                      # reading data
const_df = change_data_format(const_df)
# length = 300
# const_df = choose_n_random(const_df, length)
min_prox_mat, min_cnty_index = create_proximity_matrix(const_df, 'DTW')
max_prox_mat, max_cnty_index = create_proximity_matrix(const_df, 'Euclidean')
@app.callback(
    [
        Output(component_id='my_bee_map2', component_property='figure'),
        Output(component_id='k_value', component_property='options')
     ],
    [
        # Input(component_id='dataset', component_property='value'),
        Input(component_id='k_value', component_property='value'),
        Input(component_id='distance', component_property='value'),
        Input(component_id='inter_cluster', component_property='value'),
    ]
)
def update(k_value, distance, inter_cluster):
    if distance == 'DTW':
        prox_mat = min_prox_mat
        cnty_index = min_cnty_index
    else:
        prox_mat = max_prox_mat
        cnty_index = max_cnty_index
    dff = const_df
    dff = create_hierarchical_clusters(prox_mat, cnty_index, k=k_value, inter_cluster=inter_cluster)
    dff = change_cluster_index(dff)
    # print(dff.head())
    fig = px.choropleth(dff,
                        locationmode='country names',
                        locations="Country",
                        color="Cluster",  # lifeExp is a column of gapminder
                        hover_name="Country",  # column to add to hover information
                        color_continuous_scale=px.colors.sequential.Turbo
                        # labels={'Cluster': label[dataset]}
    )

    k_values = [{'label': k, 'value': k} for k in range(1, len(set(df.Country.tolist())) + 1, 5)]
    print('computations for the second graph is completed')
    return [fig, k_values]


# ------------------------------------------------------------------------------
if __name__ == '__main__':
    app.run_server(debug=True)

