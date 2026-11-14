import numpy as np
import plotly.graph_objects as go

def raster_figure(values, title, transform, crs, changes=False):
    # Display sampling only: the scientific arrays and point queries stay at native resolution.
    step = max(1, int(np.ceil(max(values.shape)/650)))
    z = values[::step, ::step]
    xs = transform.c + (np.arange(0, values.shape[1], step)+.5)*transform.a
    ys = transform.f + (np.arange(0, values.shape[0], step)+.5)*transform.e
    fig = go.Figure(go.Heatmap(z=z, x=xs, y=ys, zmin=-6 if changes else -30, zmax=6 if changes else 10, colorscale=[[0,"#205b87"],[.5,"#f2f2e8"],[1,"#c6601c"]], colorbar={"title":"dB"}, hoverongaps=False))
    fig.update_layout(title=title, xaxis_title=f"Este (m) · {crs}", yaxis_title="Norte (m)", height=540, margin={"l":45,"r":15,"t":45,"b":40})
    fig.update_yaxes(scaleanchor="x", scaleratio=1)
    return fig

