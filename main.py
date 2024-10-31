"""
Author: Vaasudevan Srinivasan
Created: Oct 31, 2024
Modified: Oct 31, 2024
Description: Streamlit app to visualize NLCD dataset for US counties
"""

import base64
import logging
import time

import geopandas as gpd
import imageio
import numpy as np
import rasterio as rio
import streamlit as st
from rasterio.mask import raster_geometry_mask

logging.getLogger('rasterio').setLevel(logging.ERROR)


URL = 'https://s3-us-west-2.amazonaws.com/mrlc/Annual_NLCD_LndCov_{year}_CU_C1V0.tif'

USA = gpd.read_file(
    'https://geodata.ucdavis.edu/diva/adm/USA_adm.zip',
    layer='USA_adm2',
    engine='pyogrio',
    use_arrow=True
)


def get_extent(state, county):
    with rio.open(URL.format(year=1985)) as src:
        return (
            USA.query(f'NAME_1 == "{state}" and NAME_2 == "{county}"')
            .to_crs(src.profile['crs'])
            .geometry
            .squeeze()
        )


def main(start, stop, step, state, county):
    """ """

    images = []
    with st.status('Processing', expanded=True) as status:

        start_time = time.perf_counter()
        for year in range(start, stop, step):
            st.write(f'Dowloading {year} NLCD image for {county}')

            with rio.open(URL.format(year=year)) as src:

                # Read only for the county and mask out rest of the areas
                mask, transform, win = raster_geometry_mask(
                    src, [get_extent(state, county)], crop=True, invert=False
                )
                data = src.read(1, window=win)
                data[mask] = src.nodata

                # Assign color codes from the palette
                rgb_image = np.zeros((*data.shape, 4), dtype=np.uint8)
                for cls, rgb in src.colormap(1).items():
                    rgb_image[data == cls] = rgb[:4]
                images.append(rgb_image)

        st.write('Preparing GIF')
        imageio.mimsave('nlcd.gif', images, fps=4, loop=0)
        end_time = time.perf_counter()
        status.update(
            label=f'Done. Took {end_time - start_time:.0f} seconds',
            state='complete',
            expanded=False
        )

    # https://discuss.streamlit.io/t/how-to-show-local-gif-image/3408/4
    with open('nlcd.gif', 'rb') as file_:
        contents = file_.read()
        data_url = base64.b64encode(contents).decode('utf-8')
        st.markdown(
            f'<img src="data:image/gif;base64,{data_url}" width=60% height=60%>',
            unsafe_allow_html=True,
        )


def ui():
    """ """

    st.set_page_config(page_title='NLCD-County', layout='wide')

    with st.sidebar:
        st.title('National Land Cover Database 🗺️')
        start = st.number_input('Start:', min_value=1985, max_value=2023)
        stop = st.number_input('Stop:', min_value=1985, max_value=2023, value=2023)
        step = st.number_input('Step:', min_value=1, max_value=10, value=8)
        st.image('legend.jpg', use_column_width=True)

    col1, col2 = st.columns(2)
    with col1:
        state = st.selectbox('State:', ['Select'] + list(USA.NAME_1.unique()))
    with col2:
        county = 'Select'
        if state != 'Select':
            state_counties = list(USA.query(f'NAME_1 == "{state}"').NAME_2.unique())
            county = st.selectbox('County:', ['Select'] + state_counties)

    if county != 'Select':
        main(start, stop, step, state, county)


if __name__ == '__main__':
    ui()
