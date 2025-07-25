#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2017-2018 Satpy developers
#
# This file is part of satpy.
#
# satpy is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# satpy is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# satpy.  If not, see <http://www.gnu.org/licenses/>.

"""Common functionality for SEVIRI L1.5 data readers.

Calibration
-----------

This section describes how to control the calibration of SEVIRI L1.5 data.


Calibration to radiance
^^^^^^^^^^^^^^^^^^^^^^^

The SEVIRI L1.5 data readers allow for choosing between two file-internal
calibration coefficients to convert counts to radiances:

    - Nominal for all channels (default)
    - GSICS where available (IR currently) and nominal for the remaining
      channels (VIS & HRV currently)

In order to change the default behaviour, use the ``reader_kwargs`` keyword
argument upon Scene creation::

    import satpy
    scene = satpy.Scene(filenames=filenames,
                        reader='seviri_l1b_...',
                        reader_kwargs={'calib_mode': 'GSICS'})
    scene.load(['VIS006', 'IR_108'])

In addition, two other calibration methods are available:

1. It is possible to specify external calibration coefficients for the
   conversion from counts to radiances. External coefficients take
   precedence over internal coefficients and over the Meirink
   coefficients, but you can also mix internal and external coefficients:
   If external calibration coefficients are specified for only a subset
   of channels, the remaining channels will be calibrated using the
   chosen file-internal coefficients (nominal or GSICS).  Calibration
   coefficients must be specified in [mW m-2 sr-1 (cm-1)-1].

2. The calibration mode ``meirink-2023`` uses coefficients based on an
   intercalibration with Aqua-MODIS for the visible channels, as found in
   `Inter-calibration of polar imager solar channels using SEVIRI`_
   (2013) by J. F. Meirink, R. A. Roebeling, and P. Stammes.


In the following example we use external calibration coefficients for the
``VIS006`` & ``IR_108`` channels, and nominal coefficients for the
remaining channels::

    coefs = {'VIS006': {'gain': 0.0236, 'offset': -1.20},
             'IR_108': {'gain': 0.2156, 'offset': -10.4}}
    scene = satpy.Scene(filenames,
                        reader='seviri_l1b_...',
                        reader_kwargs={'ext_calib_coefs': coefs})
    scene.load(['VIS006', 'VIS008', 'IR_108', 'IR_120'])

In the next example we use external calibration coefficients for the
``VIS006`` & ``IR_108`` channels, GSICS coefficients where available
(other IR channels) and nominal coefficients for the rest::

    coefs = {'VIS006': {'gain': 0.0236, 'offset': -1.20},
             'IR_108': {'gain': 0.2156, 'offset': -10.4}}
    scene = satpy.Scene(filenames,
                        reader='seviri_l1b_...',
                        reader_kwargs={'calib_mode': 'GSICS',
                                       'ext_calib_coefs': coefs})
    scene.load(['VIS006', 'VIS008', 'IR_108', 'IR_120'])

In the next example we use the mode ``meirink-2023`` calibration
coefficients for all visible channels and nominal coefficients for the
rest::

    scene = satpy.Scene(filenames,
                        reader='seviri_l1b_...',
                        reader_kwargs={'calib_mode': 'meirink-2023'})
    scene.load(['VIS006', 'VIS008', 'IR_016'])


Calibration to reflectance
^^^^^^^^^^^^^^^^^^^^^^^^^^

When loading solar channels, the SEVIRI L1.5 data readers apply a correction for
the Sun-Earth distance variation throughout the year - as recommended by
the EUMETSAT document
`Conversion from radiances to reflectances for SEVIRI warm channels`_.
In the unlikely situation that this correction is not required, it can be
removed on a per-channel basis using
:func:`satpy.readers.core.utils.remove_earthsun_distance_correction`.


Masking of bad quality scan lines
---------------------------------

By default bad quality scan lines are masked and replaced with ``np.nan`` for radiance, reflectance and
brightness temperature calibrations based on the quality flags provided by the data (for details on quality
flags see `MSG Level 1.5 Image Data Format Description`_ page 109). To disable masking
``reader_kwargs={'mask_bad_quality_scan_lines': False}`` can be passed to the Scene.


Metadata
--------

The SEVIRI L1.5 readers provide the following metadata:

* The ``orbital_parameters`` attribute provides the nominal and actual satellite
  position, as well as the projection centre. See the `Metadata` section in
  the :doc:`../reading` chapter for more information.

* The ``acq_time`` coordinate provides the mean acquisition time for each
  scanline. Use a ``MultiIndex`` to enable selection by acquisition time:

  .. code-block:: python

      import pandas as pd
      mi = pd.MultiIndex.from_arrays([scn['IR_108']['y'].data, scn['IR_108']['acq_time'].data],
                                     names=('y_coord', 'time'))
      scn['IR_108']['y'] = mi
      scn['IR_108'].sel(time=np.datetime64('2019-03-01T12:06:13.052000000'))

* HRIT and Native readers can add raw metadata from the file header, such
  as calibration coefficients, to dataset attributes. Use the reader keyword
  argument ``include_raw_metadata``. Here's an example for extracting
  calibration coefficients from Native files.

  .. code-block:: python

       scene = satpy.Scene(filenames,
                           reader='seviri_l1b_native',
                           reader_kwargs={'include_raw_metadata': True})
       scene.load(["IR_108"])
       mda = scene["IR_108"].attrs["raw_metadata"]
       coefs = mda["15_DATA_HEADER"]["RadiometricProcessing"]["Level15ImageCalibration"]

  Note that this comes with a performance penalty of up to 10% if raw metadata from
  multiple segments or scans need to be combined. By default, arrays with more
  than 100 elements are excluded to limit the performance penalty. This
  threshold can be adjusted using the ``mda_max_array_size`` reader keyword
  argument:

  .. code-block:: python

       scene = satpy.Scene(filenames,
                           reader='seviri_l1b_native',
                           reader_kwargs={'include_raw_metadata': True,
                                         'mda_max_array_size': 1000})

References:
    - `MSG Level 1.5 Image Data Format Description`_
    - `Radiometric Calibration of MSG SEVIRI Level 1.5 Image Data in Equivalent Spectral Blackbody Radiance`_

.. _Conversion from radiances to reflectances for SEVIRI warm channels:
    https://www-cdn.eumetsat.int/files/2020-04/pdf_msg_seviri_rad2refl.pdf

.. _MSG Level 1.5 Image Data Format Description:
    https://www.eumetsat.int/media/45126

.. _Radiometric Calibration of MSG SEVIRI Level 1.5 Image Data in Equivalent Spectral Blackbody Radiance:
    https://www-cdn.eumetsat.int/files/2020-04/pdf_ten_msg_seviri_rad_calib.pdf

.. _Inter-calibration of polar imager solar channels using SEVIRI:
   http://dx.doi.org/10.5194/amt-6-2495-2013

"""
from __future__ import annotations

import datetime as dt
import warnings
from collections import namedtuple
from collections.abc import Iterable, Sequence

import dask.array as da
import numpy as np
import pyproj
from numpy.polynomial.chebyshev import Chebyshev

import satpy.readers.core.utils as utils
from satpy.readers.core.eum import issue_revision, time_cds_short
from satpy.utils import get_legacy_chunk_size

CHUNK_SIZE = get_legacy_chunk_size()
PLATFORM_DICT = {
    "MET08": "Meteosat-8",
    "MET09": "Meteosat-9",
    "MET10": "Meteosat-10",
    "MET11": "Meteosat-11",
    "MSG1": "Meteosat-8",
    "MSG2": "Meteosat-9",
    "MSG3": "Meteosat-10",
    "MSG4": "Meteosat-11",
}

REPEAT_CYCLE_DURATION = 15

REPEAT_CYCLE_DURATION_RSS = 5

C1 = 1.19104273e-5
C2 = 1.43877523

VISIR_NUM_COLUMNS = 3712
VISIR_NUM_LINES = 3712
HRV_NUM_COLUMNS = 11136
HRV_NUM_LINES = 11136

CHANNEL_NAMES = {1: "VIS006",
                 2: "VIS008",
                 3: "IR_016",
                 4: "IR_039",
                 5: "WV_062",
                 6: "WV_073",
                 7: "IR_087",
                 8: "IR_097",
                 9: "IR_108",
                 10: "IR_120",
                 11: "IR_134",
                 12: "HRV"}

VIS_CHANNELS = ["HRV", "VIS006", "VIS008", "IR_016"]

# Polynomial coefficients for spectral-effective BT fits
BTFIT = dict()
# [A, B, C]
BTFIT["IR_039"] = [0.0, 1.011751900, -3.550400]
BTFIT["WV_062"] = [0.00001805700, 1.000255533, -1.790930]
BTFIT["WV_073"] = [0.00000231818, 1.000668281, -0.456166]
BTFIT["IR_087"] = [-0.00002332000, 1.011803400, -1.507390]
BTFIT["IR_097"] = [-0.00002055330, 1.009370670, -1.030600]
BTFIT["IR_108"] = [-0.00007392770, 1.032889800, -3.296740]
BTFIT["IR_120"] = [-0.00007009840, 1.031314600, -3.181090]
BTFIT["IR_134"] = [-0.00007293450, 1.030424800, -2.645950]

SATNUM = {321: "8",
          322: "9",
          323: "10",
          324: "11"}

CALIB = dict()

# Meteosat 8
CALIB[321] = {"HRV": {"F": 78.7599},
              "VIS006": {"F": 65.2296},
              "VIS008": {"F": 73.0127},
              "IR_016": {"F": 62.3715},
              "IR_039": {"VC": 2567.33,
                         "ALPHA": 0.9956,
                         "BETA": 3.41},
              "WV_062": {"VC": 1598.103,
                         "ALPHA": 0.9962,
                         "BETA": 2.218},
              "WV_073": {"VC": 1362.081,
                         "ALPHA": 0.9991,
                         "BETA": 0.478},
              "IR_087": {"VC": 1149.069,
                         "ALPHA": 0.9996,
                         "BETA": 0.179},
              "IR_097": {"VC": 1034.343,
                         "ALPHA": 0.9999,
                         "BETA": 0.06},
              "IR_108": {"VC": 930.647,
                         "ALPHA": 0.9983,
                         "BETA": 0.625},
              "IR_120": {"VC": 839.66,
                         "ALPHA": 0.9988,
                         "BETA": 0.397},
              "IR_134": {"VC": 752.387,
                         "ALPHA": 0.9981,
                         "BETA": 0.578}}

# Meteosat 9
CALIB[322] = {"HRV": {"F": 79.0113},
              "VIS006": {"F": 65.2065},
              "VIS008": {"F": 73.1869},
              "IR_016": {"F": 61.9923},
              "IR_039": {"VC": 2568.832,
                         "ALPHA": 0.9954,
                         "BETA": 3.438},
              "WV_062": {"VC": 1600.548,
                         "ALPHA": 0.9963,
                         "BETA": 2.185},
              "WV_073": {"VC": 1360.330,
                         "ALPHA": 0.9991,
                         "BETA": 0.47},
              "IR_087": {"VC": 1148.620,
                         "ALPHA": 0.9996,
                         "BETA": 0.179},
              "IR_097": {"VC": 1035.289,
                         "ALPHA": 0.9999,
                         "BETA": 0.056},
              "IR_108": {"VC": 931.7,
                         "ALPHA": 0.9983,
                         "BETA": 0.64},
              "IR_120": {"VC": 836.445,
                         "ALPHA": 0.9988,
                         "BETA": 0.408},
              "IR_134": {"VC": 751.792,
                         "ALPHA": 0.9981,
                         "BETA": 0.561}}

# Meteosat 10
CALIB[323] = {"HRV": {"F": 78.9416},
              "VIS006": {"F": 65.5148},
              "VIS008": {"F": 73.1807},
              "IR_016": {"F": 62.0208},
              "IR_039": {"VC": 2547.771,
                         "ALPHA": 0.9915,
                         "BETA": 2.9002},
              "WV_062": {"VC": 1595.621,
                         "ALPHA": 0.9960,
                         "BETA": 2.0337},
              "WV_073": {"VC": 1360.337,
                         "ALPHA": 0.9991,
                         "BETA": 0.4340},
              "IR_087": {"VC": 1148.130,
                         "ALPHA": 0.9996,
                         "BETA": 0.1714},
              "IR_097": {"VC": 1034.715,
                         "ALPHA": 0.9999,
                         "BETA": 0.0527},
              "IR_108": {"VC": 929.842,
                         "ALPHA": 0.9983,
                         "BETA": 0.6084},
              "IR_120": {"VC": 838.659,
                         "ALPHA": 0.9988,
                         "BETA": 0.3882},
              "IR_134": {"VC": 750.653,
                         "ALPHA": 0.9982,
                         "BETA": 0.5390}}

# Meteosat 11
CALIB[324] = {"HRV": {"F": 79.0035},
              "VIS006": {"F": 65.2656},
              "VIS008": {"F": 73.1692},
              "IR_016": {"F": 61.9416},
              "IR_039": {"VC": 2555.280,
                         "ALPHA": 0.9916,
                         "BETA": 2.9438},
              "WV_062": {"VC": 1596.080,
                         "ALPHA": 0.9959,
                         "BETA": 2.0780},
              "WV_073": {"VC": 1361.748,
                         "ALPHA": 0.9990,
                         "BETA": 0.4929},
              "IR_087": {"VC": 1147.433,
                         "ALPHA": 0.9996,
                         "BETA": 0.1731},
              "IR_097": {"VC": 1034.851,
                         "ALPHA": 0.9998,
                         "BETA": 0.0597},
              "IR_108": {"VC": 931.122,
                         "ALPHA": 0.9983,
                         "BETA": 0.6256},
              "IR_120": {"VC": 839.113,
                         "ALPHA": 0.9988,
                         "BETA": 0.4002},
              "IR_134": {"VC": 748.585,
                         "ALPHA": 0.9981,
                         "BETA": 0.5635}}

# Calibration coefficients from Meirink, J.F., R.A. Roebeling and P. Stammes, 2013:
# Inter-calibration of polar imager solar channels using SEVIRI, Atm. Meas. Tech., 6,
# 2495-2508, doi:10.5194/amt-6-2495-2013
#
# The coeffients in the 2023 entry have been obtained from the webpage
# https://msgcpp.knmi.nl/solar-channel-calibration.html on 2023-10-11.
#
# The coefficients are stored in pairs of A, B (see function `get_meirink_slope`) where the
# units of A are µW m-2 sr-1 (cm-1)-1 and those of B are µW m-2 sr-1 (cm-1)-1 (86400 s)-1
#
# To obtain the slope for the calibration, one should use the routine get_seviri_meirink_slope

# Epoch for the MEIRINK re-calibration
MEIRINK_EPOCH = dt.datetime(2000, 1, 1)

MEIRINK_COEFS: dict[str, dict[int, dict[str, tuple[float, float]]]] = {}
MEIRINK_COEFS["2023"] = {}

# Meteosat-8

MEIRINK_COEFS["2023"][321] = {"VIS006": (24.346, 0.3739),
                              "VIS008": (30.989, 0.3111),
                              "IR_016": (22.869, 0.0065)
                              }

# Meteosat-9

MEIRINK_COEFS["2023"][322] = {"VIS006": (21.026, 0.2556),
                              "VIS008": (26.875, 0.1835),
                              "IR_016": (21.394, 0.0498)
                              }

# Meteosat-10

MEIRINK_COEFS["2023"][323] = {"VIS006": (19.829, 0.5856),
                              "VIS008": (25.284, 0.6787),
                              "IR_016": (23.066, -0.0286)
                              }

# Meteosat-11

MEIRINK_COEFS["2023"][324] = {"VIS006": (20.515, 0.3600),
                              "VIS008": (25.803, 0.4844),
                              "IR_016": (22.354, -0.0187)
                              }


def get_cds_time(days, msecs):
    """Compute timestamp given the days since epoch and milliseconds of the day.

    1958-01-01 00:00 is interpreted as fill value and will be replaced by NaT (Not a Time).

    Args:
        days (int, numpy.ndarray):
            Days since 1958-01-01
        msecs (int, numpy.ndarray):
            Milliseconds of the day

    Returns:
        numpy.datetime64: Timestamp(s)

    """
    if np.isscalar(days):
        days = np.array([days], dtype="int64")
        msecs = np.array([msecs], dtype="int64")

    # use nanosecond precision to silence warning from XArray
    nsecs = 1000000 * msecs.astype("timedelta64[ns]")
    time = np.datetime64("1958-01-01").astype("datetime64[ms]") + \
        days.astype("timedelta64[D]") + nsecs
    time[time == np.datetime64("1958-01-01 00:00")] = np.datetime64("NaT")

    if len(time) == 1:
        return time[0]
    return time


def add_scanline_acq_time(dataset, acq_time):
    """Add scanline acquisition time to the given dataset."""
    dataset.coords["acq_time"] = ("y", acq_time)
    dataset.coords["acq_time"].attrs[
        "long_name"] = "Mean scanline acquisition time"


def dec10216(inbuf):
    """Decode 10 bits data into 16 bits words.

    ::

        /*
         * pack 4 10-bit words in 5 bytes into 4 16-bit words
         *
         * 0       1       2       3       4       5
         * 01234567890123456789012345678901234567890
         * 0         1         2         3         4
         */
        ip = &in_buffer[i];
        op = &out_buffer[j];
        op[0] = ip[0]*4 + ip[1]/64;
        op[1] = (ip[1] & 0x3F)*16 + ip[2]/16;
        op[2] = (ip[2] & 0x0F)*64 + ip[3]/4;
        op[3] = (ip[3] & 0x03)*256 +ip[4];

    """
    arr10 = inbuf.astype(np.uint16)
    arr16_len = int(len(arr10) * 4 / 5)
    arr10_len = int((arr16_len * 5) / 4)
    arr10 = arr10[:arr10_len]  # adjust size

    # dask is slow with indexing
    arr10_0 = arr10[::5]
    arr10_1 = arr10[1::5]
    arr10_2 = arr10[2::5]
    arr10_3 = arr10[3::5]
    arr10_4 = arr10[4::5]

    arr16_0 = (arr10_0 << 2) + (arr10_1 >> 6)
    arr16_1 = ((arr10_1 & 63) << 4) + (arr10_2 >> 4)
    arr16_2 = ((arr10_2 & 15) << 6) + (arr10_3 >> 2)
    arr16_3 = ((arr10_3 & 3) << 8) + arr10_4
    arr16 = np.stack([arr16_0, arr16_1, arr16_2, arr16_3], axis=-1).ravel()

    return arr16


class MpefProductHeader(object):
    """MPEF product header class."""

    def get(self):
        """Return numpy record_array for MPEF product header."""
        record = [
            ("MPEF_File_Id", np.int16),
            ("MPEF_Header_Version", np.uint8),
            ("ManualDissAuthRequest", bool),
            ("ManualDisseminationAuth", bool),
            ("DisseminationAuth", bool),
            ("NominalTime", time_cds_short),
            ("ProductQuality", np.uint8),
            ("ProductCompleteness", np.uint8),
            ("ProductTimeliness", np.uint8),
            ("ProcessingInstanceId", np.int8),
            ("ImagesUsed", self.images_used, (4,)),
            ("BaseAlgorithmVersion",
             issue_revision),
            ("ProductAlgorithmVersion",
             issue_revision),
            ("InstanceServerName", "S2"),
            ("SpacecraftName", "S2"),
            ("Mission", "S3"),
            ("RectificationLongitude", "S5"),
            ("Encoding", "S1"),
            ("TerminationSpace", "S1"),
            ("EncodingVersion", np.uint16),
            ("Channel", np.uint8),
            ("ImageLocation", "S3"),
            ("GsicsCalMode", np.bool_),
            ("GsicsCalValidity", np.bool_),
            ("Padding", "S2"),
            ("OffsetToData", np.uint32),
            ("Padding2", "S9"),
            ("RepeatCycle", "S15"),
        ]

        return np.dtype(record).newbyteorder(">")

    @property
    def images_used(self):
        """Return structure for images_used."""
        record = [
            ("Padding1", "S2"),
            ("ExpectedImage", time_cds_short),
            ("ImageReceived", bool),
            ("Padding2", "S1"),
            ("UsedImageStart_Day", np.uint16),
            ("UsedImageStart_Millsec", np.uint32),
            ("Padding3", "S2"),
            ("UsedImageEnd_Day", np.uint16),
            ("UsedImageEndt_Millsec", np.uint32),
        ]

        return record


mpef_product_header = MpefProductHeader().get()


class SEVIRICalibrationAlgorithm:
    """SEVIRI calibration algorithms."""

    def __init__(self, platform_id, scan_time):
        """Initialize the calibration algorithm."""
        self._platform_id = platform_id
        self._scan_time = scan_time

    def convert_to_radiance(self, data, gain, offset):
        """Calibrate to radiance."""
        data = data.where(data > 0)
        return (data * gain + offset).clip(0.0, None)

    def _erads2bt(self, data, channel_name):
        """Convert effective radiance to brightness temperature."""
        cal_info = CALIB[self._platform_id][channel_name]
        alpha = cal_info["ALPHA"]
        beta = cal_info["BETA"]
        wavenumber = CALIB[self._platform_id][channel_name]["VC"]

        return (self._tl15(data, wavenumber) - beta) / alpha

    def ir_calibrate(self, data, channel_name, cal_type):
        """Calibrate to brightness temperature."""
        if cal_type == 1:
            # spectral radiances
            return self._srads2bt(data, channel_name)
        elif cal_type == 2:
            # effective radiances
            return self._erads2bt(data, channel_name)
        else:
            raise NotImplementedError("Unknown calibration type")

    def _srads2bt(self, data, channel_name):
        """Convert spectral radiance to brightness temperature."""
        a__, b__, c__ = BTFIT[channel_name]
        wavenumber = CALIB[self._platform_id][channel_name]["VC"]
        temp = self._tl15(data, wavenumber)

        return a__ * temp * temp + b__ * temp + c__

    def _tl15(self, data, wavenumber):
        """Compute the L15 temperature."""
        return ((C2 * wavenumber) /
                np.log((1.0 / data) * C1 * wavenumber ** 3 + 1.0))

    def vis_calibrate(self, data, solar_irradiance):
        """Calibrate to reflectance.

        This uses the method described in Conversion from radiances to
        reflectances for SEVIRI warm channels: https://www-cdn.eumetsat.int/files/2020-04/pdf_msg_seviri_rad2refl.pdf
        """
        reflectance = np.pi * data * 100.0 / solar_irradiance
        return utils.apply_earthsun_distance_correction(reflectance, self._scan_time)


CalibParams = namedtuple("CalibParams", ["mode", "internal_coefs", "external_coefs", "radiance_type"])
ScanParams = namedtuple("ScanParams", ["platform_id", "channel_name", "scan_time"])


class SEVIRICalibrationHandler:
    """Calibration handler for SEVIRI HRIT-, native- and netCDF-formats.

    Handles selection of calibration coefficients and calls the appropriate
    calibration algorithm.
    """

    def __init__(self, calib_params, scan_params):
        """Initialize the calibration handler."""
        self._calib_params = calib_params
        self._scan_params = scan_params
        self._algo = SEVIRICalibrationAlgorithm(
            platform_id=scan_params.platform_id,
            scan_time=scan_params.scan_time
        )
        self._check_calib_mode(calib_params.mode)

    def _check_calib_mode(self, calib_mode):
        valid_modes = ("NOMINAL", "GSICS", "MEIRINK-2023")
        if calib_mode not in valid_modes:
            raise ValueError(
                "Invalid calibration mode: {}. Choose one of {}".format(
                    calib_mode, valid_modes)
            )

    def calibrate(self, data, calibration):
        """Calibrate the given data."""
        if calibration == "counts":
            res = data
        elif calibration in ["radiance", "reflectance",
                             "brightness_temperature"]:
            coefs = self.get_coefs()
            res = self._algo.convert_to_radiance(
                data.astype(np.float32),
                np.float32(coefs["coefs"]["gain"]),
                np.float32(coefs["coefs"]["offset"])
            )
        else:
            raise ValueError(
                "Invalid calibration {} for channel {}".format(
                    calibration, self._scan_params.channel_name
                )
            )

        if calibration == "reflectance":
            solar_irradiance = CALIB[self._scan_params.platform_id][self._scan_params.channel_name]["F"]
            res = self._algo.vis_calibrate(res, solar_irradiance)
        elif calibration == "brightness_temperature":
            res = self._algo.ir_calibrate(
                res, self._scan_params.channel_name, self._calib_params.radiance_type
            )
        return res

    def get_coefs(self):
        """Get calibration coefficients."""
        picker = utils.CalibrationCoefficientPicker(self._calib_params.internal_coefs,
                                                    self._get_calib_wishlist(),
                                                    default="NOMINAL",
                                                    fallback="NOMINAL")
        return picker.get_coefs(self._scan_params.channel_name)

    def _get_calib_wishlist(self):
        ext_coefs = self._calib_params.external_coefs or {}
        wishlist = {
            ch: self._calib_params.mode for ch in CHANNEL_NAMES.values()
        }
        return wishlist | ext_coefs


def chebyshev(coefs: Sequence | np.ndarray, time: int | float, domain: Iterable):
    """Evaluate a Chebyshev Polynomial.

    Args:
        coefs: Coefficients defining the polynomial
        time: Time where to evaluate the polynomial
        domain: Domain (or time interval) for which the polynomial is defined: [left, right]
    Reference: Appendix A in the MSG Level 1.5 Image Data Format Description.

    """
    return Chebyshev(coefs, domain=domain)(time) - 0.5 * coefs[0]


def chebyshev_3d(coefs, time, domain):
    """Evaluate Chebyshev Polynomials for three dimensions (x, y, z).

    Expects the three coefficient sets to be defined in the same domain.

    Args:
        coefs: (x, y, z) coefficient sets.
        time: See :func:`chebyshev`
        domain: See :func:`chebyshev`

    Returns:
        Polynomials evaluated in (x, y, z) dimension.
    """
    x_coefs, y_coefs, z_coefs = coefs
    x = chebyshev(x_coefs, time, domain)
    y = chebyshev(y_coefs, time, domain)
    z = chebyshev(z_coefs, time, domain)
    return x, y, z


class NoValidOrbitParams(Exception):
    """Exception when validOrbitParameters are missing."""

    pass


class OrbitPolynomial:
    """Polynomial encoding the satellite position.

    Satellite position as a function of time is encoded in the coefficients
    of an 8th-order Chebyshev polynomial.
    """

    def __init__(self, coefs, start_time, end_time):
        """Initialize the polynomial."""
        self.coefs = coefs
        self.start_time = start_time
        self.end_time = end_time

    def evaluate(self, time):
        """Get satellite position in earth-centered cartesian coordinates.

        Args:
            time: Timestamp where to evaluate the polynomial

        Returns:
            Earth-centered cartesian coordinates (x, y, z) in meters
        """
        domain = [np.datetime64(self.start_time).astype("int64"),
                  np.datetime64(self.end_time).astype("int64")]
        time = np.datetime64(time).astype("int64")
        x, y, z = chebyshev_3d(self.coefs, time, domain)
        return x * 1000, y * 1000, z * 1000  # km -> m

    def __eq__(self, other):
        """Test equality of two orbit polynomials."""
        return (
            np.array_equal(self.coefs, np.array(other.coefs)) and
            self.start_time == other.start_time and
            self.end_time == other.end_time
        )


def get_satpos(orbit_polynomial, time, semi_major_axis, semi_minor_axis):
    """Get satellite position in geodetic coordinates.

    Args:
        orbit_polynomial: OrbitPolynomial instance
        time: Timestamp where to evaluate the polynomial
        semi_major_axis: Semi-major axis of the ellipsoid
        semi_minor_axis: Semi-minor axis of the ellipsoid

    Returns:
        Longitude [deg east], Latitude [deg north] and Altitude [m]
    """
    x, y, z = orbit_polynomial.evaluate(time)
    geocent = pyproj.CRS(
        proj="geocent", a=semi_major_axis, b=semi_minor_axis, units="m"
    )
    latlong = pyproj.CRS(
        proj="latlong", a=semi_major_axis, b=semi_minor_axis, units="m"
    )
    transformer = pyproj.Transformer.from_crs(geocent, latlong)
    lon, lat, alt = transformer.transform(x, y, z)
    return lon, lat, alt


class OrbitPolynomialFinder:
    """Find orbit polynomial for a given timestamp."""

    def __init__(self, orbit_polynomials):
        """Initialize with the given candidates.

        Args:
            orbit_polynomials: Dictionary of orbit polynomials as found in
                               SEVIRI L1B files:

                               .. code-block:: python

                                   {'X': x_polynomials,
                                    'Y': y_polynomials,
                                    'Z': z_polynomials,
                                    'StartTime': polynomials_valid_from,
                                    'EndTime': polynomials_valid_to}

        """
        self.orbit_polynomials = orbit_polynomials
        # Left/right boundaries of time intervals for which the polynomials are
        # valid.
        self.valid_from = orbit_polynomials["StartTime"][0, :].astype(
            "datetime64[us]")
        self.valid_to = orbit_polynomials["EndTime"][0, :].astype(
            "datetime64[us]")

    def get_orbit_polynomial(self, time, max_delta=6):
        """Get orbit polynomial valid for the given time.

        Orbit polynomials are only valid for certain time intervals. Find the
        polynomial, whose corresponding interval encloses the given timestamp.
        If there are multiple enclosing intervals, use the most recent one.
        If there is no enclosing interval, find the interval whose centre is
        closest to the given timestamp (but not more than ``max_delta`` hours
        apart).

        Why are there gaps between those intervals? Response from EUM:

        A manoeuvre is a discontinuity in the orbit parameters. The flight
        dynamic algorithms are not made to interpolate over the time-span of
        the manoeuvre; hence we have elements describing the orbit before a
        manoeuvre and a new set of elements describing the orbit after the
        manoeuvre. The flight dynamic products are created so that there is
        an intentional gap at the time of the manoeuvre. Also the two
        pre-manoeuvre elements may overlap. But the overlap is not of an
        issue as both sets of elements describe the same pre-manoeuvre orbit
        (with negligible variations).
        """
        time = np.datetime64(time)
        try:
            match = self._get_enclosing_interval(time)
        except ValueError:
            warnings.warn(
                "No orbit polynomial valid for {}. Using closest "
                "match.".format(time),
                stacklevel=2
            )
            match = self._get_closest_interval_within(time, max_delta)
        return OrbitPolynomial(
            coefs=(
                self.orbit_polynomials["X"][match],
                self.orbit_polynomials["Y"][match],
                self.orbit_polynomials["Z"][match]
            ),
            start_time=self.valid_from[match],
            end_time=self.valid_to[match]
        )

    def _get_enclosing_interval(self, time):
        """Find interval enclosing the given timestamp."""
        enclosing = np.where(
            np.logical_and(
                time >= self.valid_from,
                time < self.valid_to
            )
        )[0]
        most_recent = np.argmax(self.valid_from[enclosing])
        return enclosing[most_recent]

    def _get_closest_interval_within(self, time, threshold):
        """Find interval closest to the given timestamp within a given distance.

        Args:
            time: Timestamp of interest
            threshold: Maximum distance between timestamp and interval center

        Returns:
            Index of closest interval
        """
        closest_match, distance = self._get_closest_interval(time)
        threshold_diff = np.timedelta64(threshold, "h")
        if distance < threshold_diff:
            return closest_match
        raise NoValidOrbitParams(
            "Unable to find orbit coefficients valid for {} +/- {}"
            "hours".format(time, threshold)
        )

    def _get_closest_interval(self, time):
        """Find interval closest to the given timestamp.

        Returns:
            Index of closest interval, distance from its center
        """
        intervals_centre = self.valid_from + 0.5 * (
                self.valid_to - self.valid_from
        )
        diffs_us = (time - intervals_centre).astype("i8")
        closest_match = np.argmin(np.fabs(diffs_us))
        distance = abs(intervals_centre[closest_match] - time)
        return closest_match, distance


# def calculate_area_extent(center_point, north, east, south, west, we_offset, ns_offset, column_step, line_step):
def calculate_area_extent(area_dict):
    """Calculate the area extent seen by a geostationary satellite.

    Args:
        area_dict: A dictionary containing the required parameters
            center_point: Center point for the projection
            north: Northmost row number
            east: Eastmost column number
            west: Westmost column number
            south: Southmost row number
            column_step: Pixel resolution in meters in east-west direction
            line_step: Pixel resolution in meters in south-north direction
            [column_offset: Column offset, defaults to 0 if not given]
            [line_offset: Line offset, defaults to 0 if not given]

    Returns:
        tuple: An area extent for the scene defined by the lower left and
               upper right corners

    # For Earth model 2 and full disk VISIR, (center_point - west - 0.5 + we_offset) must be -1856.5 .
    # See MSG Level 1.5 Image Data Format Description Figure 7 - Alignment and numbering of the non-HRV pixels.
    """
    center_point = area_dict["center_point"]
    east = area_dict["east"]
    west = area_dict["west"]
    south = area_dict["south"]
    north = area_dict["north"]
    column_step = area_dict["column_step"]
    line_step = area_dict["line_step"]
    column_offset = area_dict.get("column_offset", 0)
    line_offset = area_dict.get("line_offset", 0)

    ll_c = (center_point - east + 0.5 + column_offset) * column_step
    ll_l = (north - center_point + 0.5 + line_offset) * line_step
    ur_c = (center_point - west - 0.5 + column_offset) * column_step
    ur_l = (south - center_point - 0.5 + line_offset) * line_step

    return (ll_c, ll_l, ur_c, ur_l)


def create_coef_dict(nominal_coefs, gsics_coefs=None, meirink_coefs=None):
    """Create coefficient dictionary expected by calibration class."""
    coefs = nominal_coefs.get_coefs()
    if gsics_coefs:
        coefs.update(gsics_coefs.get_coefs())
    if meirink_coefs:
        coefs.update(meirink_coefs.get_coefs(nominal_coefs.offset))
    return coefs


class NominalCoefficients:
    """Nominal calibration coefficients."""
    def __init__(self, channel_name, gain, offset):
        """Initialize coefficients."""
        self.channel_name = channel_name
        self.gain = gain
        self.offset = offset

    def get_coefs(self):
        """Get coefficient dictionary."""
        return {
            "NOMINAL": {
                self.channel_name: {
                    "gain": self.gain,
                    "offset": self.offset
                }
            }
        }


class GsicsCoefficients:
    """GSICS calibration coefficients."""
    def __init__(self, channel_name, gain, offset):
        """Initialize coefficients."""
        self.channel_name = channel_name
        self.gain = gain
        self.offset = offset

    def get_coefs(self):
        """Get coefficient dictionary."""
        coefs = {"GSICS": {}}
        if self._is_available():
            coefs["GSICS"][self.channel_name] = {
                "gain": self.gain,
                "offset": self.offset * self.gain
            }
        return coefs

    def _is_available(self):
        # If no GSICS coefficients are available they are set to zero in
        # the file.
        return self.gain != 0 and self.offset != 0


class MeirinkCoefficients:
    """Re-calibration of the SEVIRI visible channels slope (see Meirink 2013)."""

    def __init__(self, platform_id, channel_name, scan_time):
        """Initialize coefficients."""
        self.platform_id = platform_id
        self.channel_name = channel_name
        self.scan_time = scan_time

    def get_coefs(self, offset):
        """Get coefficient dictionary.

        Args:
            offset: Nominal calibration offset.
        """
        gain = self._get_gain()
        return self._combine_gain_and_offset(gain, offset)

    def _get_gain(self):
        res = {}
        for version, coefs in MEIRINK_COEFS.items():
            gain = self._get_gain_single_channel(coefs)
            if gain:
                res[f"MEIRINK-{version}"] = gain
        return res

    def _get_gain_single_channel(self, coefs):
        try:
            coefs_ch = coefs[self.platform_id][self.channel_name]
            return self.get_slope(coefs_ch, self.scan_time)
        except KeyError:
            return None

    @staticmethod
    def get_slope(coefs_single_channel, acquisition_time):
        """Compute the slope for the visible channel calibration according to Meirink 2013.

        S = A + B * 1.e-3* Day

        S is here in µW m-2 sr-1 (cm-1)-1

        EUMETSAT calibration is given in mW m-2 sr-1 (cm-1)-1, so an extra factor of 1/1000 must
        be applied.
        """
        A = coefs_single_channel[0]
        B = coefs_single_channel[1]
        delta_t = (acquisition_time - MEIRINK_EPOCH).total_seconds()
        S = A + B * delta_t / (3600*24) / 1000.
        return S/1000

    def _combine_gain_and_offset(self, gain, offset):
        return {
            calib_mode: {
                self.channel_name: {"gain": gain_, "offset": offset}
            }
                for calib_mode, gain_ in gain.items()
        }

def get_padding_area(shape, dtype):
    """Create a padding area filled with no data."""
    if np.issubdtype(dtype, np.floating):
        init_value = np.nan
    else:
        init_value = 0

    padding_area = da.full(shape, init_value, dtype=dtype, chunks=CHUNK_SIZE)

    return padding_area


def pad_data_horizontally(data, final_size, east_bound, west_bound):
    """Pad the data given east and west bounds and the desired size."""
    nlines = final_size[0]
    if west_bound - east_bound != data.shape[1] - 1:
        raise IndexError("East and west bounds do not match data shape")

    padding_east = get_padding_area((nlines, east_bound - 1), data.dtype)
    padding_west = get_padding_area((nlines, (final_size[1] - west_bound)), data.dtype)

    return np.hstack((padding_east, data, padding_west))


def pad_data_vertically(data, final_size, south_bound, north_bound):
    """Pad the data given south and north bounds and the desired size."""
    ncols = final_size[1]
    if north_bound - south_bound != data.shape[0] - 1:
        raise IndexError("South and north bounds do not match data shape")

    padding_south = get_padding_area((south_bound - 1, ncols), data.dtype)
    padding_north = get_padding_area(((final_size[0] - north_bound), ncols), data.dtype)

    return np.vstack((padding_south, data, padding_north))


def _create_bad_quality_lines_mask(line_validity, line_geometric_quality, line_radiometric_quality):
    """Create bad quality scan lines mask.

    For details on quality flags see `MSG Level 1.5 Image Data Format Description`_
    page 109.

    Args:
        line_validity (numpy.ndarray):
            Quality flags with shape (nlines,).
        line_geometric_quality (numpy.ndarray):
            Quality flags with shape (nlines,).
        line_radiometric_quality (numpy.ndarray):
            Quality flags with shape (nlines,).

    Returns:
        numpy.ndarray: Indicating if the scan line is bad.
    """
    # Based on missing (2) or corrupted (3) data
    line_mask = line_validity >= 2
    line_mask &= line_validity <= 3
    # Do not use (4)
    line_mask &= line_radiometric_quality == 4
    line_mask &= line_geometric_quality == 4
    return line_mask


def mask_bad_quality(data, line_validity, line_geometric_quality, line_radiometric_quality):
    """Mask scan lines with bad quality.

    Args:
        data (xarray.DataArray):
            Channel data
        line_validity (numpy.ndarray):
            Quality flags with shape (nlines,).
        line_geometric_quality (numpy.ndarray):
            Quality flags with shape (nlines,).
        line_radiometric_quality (numpy.ndarray):
            Quality flags with shape (nlines,).

    Returns:
        xarray.DataArray: data with lines flagged as bad converted to np.nan.
    """
    line_mask = _create_bad_quality_lines_mask(line_validity, line_geometric_quality, line_radiometric_quality)
    line_mask = line_mask[:, np.newaxis]
    data = data.where(~line_mask, np.nan).astype(np.float32)
    return data


def round_nom_time(date, time_delta):
    """Round a datetime object to a multiple of a timedelta.

    date : datetime.datetime object, default now.
    time_delta : timedelta object, we round to a multiple of this, default 1 minute.
    adapted for SEVIRI from:
    https://stackoverflow.com/questions/3463930/how-to-round-the-minute-of-a-datetime-object-python
    """
    seconds = (date - date.min).seconds
    round_to = time_delta.total_seconds()

    rounding = (seconds + round_to / 2) // round_to * round_to

    return date + dt.timedelta(0, rounding - seconds, - date.microsecond)
