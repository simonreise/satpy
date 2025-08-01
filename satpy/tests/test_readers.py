#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2019, 2022, 2023 Satpy developers
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

"""Test classes and functions in the readers/__init__.py module."""

import builtins
import contextlib
import datetime as dt
import os
import sys
import unittest
import warnings
from pathlib import Path
from typing import Iterator
from unittest import mock

import numpy as np
import pytest
import xarray as xr
from pytest_lazy_fixtures import lf as lazy_fixture

from satpy.dataset.data_dict import get_key
from satpy.dataset.dataid import DataID, ModifierTuple, WavelengthRange
from satpy.readers.core.grouping import find_files_and_readers
from satpy.readers.core.remote import open_file_or_filename

# NOTE:
# The following fixtures are not defined in this file, but are used and injected by Pytest:
# - monkeypatch
# - tmp_path

# clear the config dir environment variable so it doesn't interfere
os.environ.pop("PPP_CONFIG_DIR", None)
os.environ.pop("SATPY_CONFIG_PATH", None)

local_id_keys_config = {"name": {
    "required": True,
},
    "wavelength": {
    "type": WavelengthRange,
},
    "resolution": None,
    "calibration": {
    "enum": [
        "reflectance",
        "brightness_temperature",
        "radiance",
        "counts"
    ]
},
    "polarization": None,
    "level": None,
    "modifiers": {
    "required": True,
    "default": ModifierTuple(),
    "type": ModifierTuple,
},
}

real_import = builtins.__import__


@pytest.fixture
def viirs_file(tmp_path, monkeypatch):
    """Create a dummy viirs file."""
    filename = "SVI01_npp_d20120225_t1801245_e1802487_b01708_c20120226002130255476_noaa_ops.h5"

    monkeypatch.chdir(tmp_path)
    # touch the file so it exists on disk
    open(filename, "w").close()
    return filename


@pytest.fixture
def atms_file(tmp_path, monkeypatch):
    """Create a dummy atms file."""
    filename = "SATMS_j01_d20221220_t0910240_e0921356_b26361_c20221220100456348770_cspp_dev.h5"

    monkeypatch.chdir(tmp_path)
    # touch the file so it exists on disk
    open(filename, "w").close()
    return filename


def make_dataid(**items):
    """Make a data id."""
    return DataID(local_id_keys_config, **items)


class TestDatasetDict(unittest.TestCase):
    """Test DatasetDict and its methods."""

    def setUp(self):
        """Create a test DatasetDict."""
        from satpy import DatasetDict
        self.regular_dict = regular_dict = {
            make_dataid(name="test",
                        wavelength=(0, 0.5, 1),
                        resolution=1000): "1",
            make_dataid(name="testh",
                        wavelength=(0, 0.5, 1),
                        resolution=500): "1h",
            make_dataid(name="test2",
                        wavelength=(1, 1.5, 2),
                        resolution=1000): "2",
            make_dataid(name="test3",
                        wavelength=(1.2, 1.7, 2.2),
                        resolution=1000): "3",
            make_dataid(name="test4",
                        calibration="radiance",
                        polarization="V"): "4rad",
            make_dataid(name="test4",
                        calibration="reflectance",
                        polarization="H"): "4refl",
            make_dataid(name="test5",
                        modifiers=("mod1", "mod2")): "5_2mod",
            make_dataid(name="test5",
                        modifiers=("mod2",)): "5_1mod",
            make_dataid(name="test6", level=100): "6_100",
            make_dataid(name="test6", level=200): "6_200",
        }
        self.test_dict = DatasetDict(regular_dict)

    def test_init_noargs(self):
        """Test DatasetDict init with no arguments."""
        from satpy import DatasetDict
        d = DatasetDict()
        assert isinstance(d, dict)

    def test_init_dict(self):
        """Test DatasetDict init with a regular dict argument."""
        from satpy import DatasetDict
        regular_dict = {make_dataid(name="test", wavelength=(0, 0.5, 1)): "1", }
        d = DatasetDict(regular_dict)
        assert d == regular_dict

    def test_getitem(self):
        """Test DatasetDict getitem with different arguments."""
        from satpy.tests.utils import make_dsq
        d = self.test_dict
        # access by name
        assert d["test"] == "1"
        # access by exact wavelength
        assert d[1.5] == "2"
        # access by near wavelength
        assert d[1.55] == "2"
        # access by near wavelength of another dataset
        assert d[1.65] == "3"
        # access by name with multiple levels
        assert d["test6"] == "6_100"

        assert d[make_dsq(wavelength=1.5)] == "2"
        assert d[make_dsq(wavelength=0.5, resolution=1000)] == "1"
        assert d[make_dsq(wavelength=0.5, resolution=500)] == "1h"
        assert d[make_dsq(name="test6", level=100)] == "6_100"
        assert d[make_dsq(name="test6", level=200)] == "6_200"

        # higher resolution is returned
        assert d[0.5] == "1h"
        assert d["test4"] == "4refl"
        assert d[make_dataid(name="test4", calibration="radiance")] == "4rad"
        with pytest.raises(KeyError):
            d.getitem("1h")

        # test with full tuple
        assert d[make_dsq(name="test", wavelength=(0, 0.5, 1), resolution=1000)] == "1"

    def test_get_key(self):
        """Test 'get_key' special functions."""
        from satpy.dataset import DataQuery
        d = self.test_dict
        res1 = get_key(make_dataid(name="test4"), d, calibration="radiance")
        res2 = get_key(make_dataid(name="test4"), d, calibration="radiance",
                       num_results=0)
        res3 = get_key(make_dataid(name="test4"), d, calibration="radiance",
                       num_results=3)
        assert len(res2) == 1
        assert len(res3) == 1
        res2 = res2[0]
        res3 = res3[0]
        assert res1 == res2
        assert res1 == res3
        res1 = get_key("test4", d, query=DataQuery(polarization="V"))
        assert res1 == make_dataid(name="test4", calibration="radiance", polarization="V")

        res1 = get_key(0.5, d, query=DataQuery(resolution=500))
        assert res1 == make_dataid(name="testh", wavelength=(0, 0.5, 1), resolution=500)

        res1 = get_key("test6", d, query=DataQuery(level=100))
        assert res1 == make_dataid(name="test6", level=100)

        res1 = get_key("test5", d)
        res2 = get_key("test5", d, query=DataQuery(modifiers=("mod2",)))
        res3 = get_key("test5", d, query=DataQuery(modifiers=("mod1", "mod2",)))
        assert res1 == make_dataid(name="test5", modifiers=("mod2",))
        assert res1 == res2
        assert res1 != res3

        # more than 1 result when default is to ask for 1 result
        with pytest.raises(KeyError):
            get_key("test4", d, best=False)

    def test_contains(self):
        """Test DatasetDict contains method."""
        d = self.test_dict
        assert "test" in d
        assert not d.contains("test")
        assert "test_bad" not in d
        assert 0.5 in d
        assert not d.contains(0.5)
        assert 1.5 in d
        assert 1.55 in d
        assert 1.65 in d
        assert make_dataid(name="test4", calibration="radiance") in d
        assert "test4" in d

    def test_keys(self):
        """Test keys method of DatasetDict."""
        from satpy.tests.utils import DataID
        d = self.test_dict
        assert len(d.keys()) == len(self.regular_dict.keys())
        assert all(isinstance(x, DataID) for x in d.keys())
        name_keys = d.keys(names=True)
        assert sorted(set(name_keys))[:4] == ["test", "test2", "test3", "test4"]
        wl_keys = tuple(d.keys(wavelengths=True))
        assert (0, 0.5, 1) in wl_keys
        assert (1, 1.5, 2, "µm") in wl_keys
        assert (1.2, 1.7, 2.2, "µm") in wl_keys
        assert None in wl_keys

    def test_setitem(self):
        """Test setitem method of DatasetDict."""
        d = self.test_dict
        d["new_ds"] = {"metadata": "new_ds"}
        assert d["new_ds"]["metadata"] == "new_ds"
        d[0.5] = {"calibration": "radiance"}
        assert d[0.5]["resolution"] == 500
        assert d[0.5]["name"] == "testh"


class TestReaderLoader(unittest.TestCase):
    """Test the `load_readers` function.

    Assumes that the VIIRS SDR reader exists and works.
    """

    @pytest.fixture(autouse=True)
    def inject_fixtures(self, caplog, tmp_path):  # noqa: PT004
        """Inject caplog to the test class."""
        self._caplog = caplog
        self._tmp_path = tmp_path

    def setUp(self):
        """Wrap HDF5 file handler with our own fake handler."""
        from satpy.readers.viirs_sdr import VIIRSSDRFileHandler
        from satpy.tests.reader_tests.test_viirs_sdr import FakeHDF5FileHandler2

        # http://stackoverflow.com/questions/12219967/how-to-mock-a-base-class-with-python-mock-library
        self.p = mock.patch.object(VIIRSSDRFileHandler, "__bases__", (FakeHDF5FileHandler2,))
        self.fake_handler = self.p.start()
        self.p.is_local = True

    def tearDown(self):
        """Stop wrapping the HDF5 file handler."""
        self.p.stop()

    def test_no_args(self):
        """Test no args provided.

        This should check the local directory which should have no files.
        """
        from satpy.readers.core.loading import load_readers
        ri = load_readers()
        assert ri == {}

    def test_filenames_only(self):
        """Test with filenames specified."""
        from satpy.readers.core.loading import load_readers
        ri = load_readers(filenames=["SVI01_npp_d20120225_t1801245_e1802487_b01708_c20120226002130255476_noaa_ops.h5"])
        assert list(ri.keys()) == ["viirs_sdr"]

    def test_filenames_and_reader(self):
        """Test with filenames and reader specified."""
        from satpy.readers.core.loading import load_readers
        ri = load_readers(reader="viirs_sdr",
                          filenames=["SVI01_npp_d20120225_t1801245_e1802487_b01708_c20120226002130255476_noaa_ops.h5"])
        assert list(ri.keys()) == ["viirs_sdr"]

    def test_bad_reader_name_with_filenames(self):
        """Test bad reader name with filenames provided."""
        from satpy.readers.core.loading import load_readers
        with pytest.raises(ValueError, match="No reader named: i_dont_exist"):
            load_readers(reader="i_dont_exist",
                         filenames=["SVI01_npp_d20120225_t1801245_e1802487_b01708_c20120226002130255476_noaa_ops.h5"])

    def test_filenames_as_path(self):
        """Test with filenames specified as pathlib.Path."""
        from pathlib import Path

        from satpy.readers.core.loading import load_readers
        ri = load_readers(filenames=[
            Path("SVI01_npp_d20120225_t1801245_e1802487_b01708_c20120226002130255476_noaa_ops.h5"),
        ])
        assert list(ri.keys()) == ["viirs_sdr"]

    def test_filenames_as_dict(self):
        """Test loading readers where filenames are organized by reader."""
        from satpy.readers.core.loading import load_readers
        filenames = {
            "viirs_sdr": ["SVI01_npp_d20120225_t1801245_e1802487_b01708_c20120226002130255476_noaa_ops.h5"],
        }
        ri = load_readers(filenames=filenames)
        assert list(ri.keys()) == ["viirs_sdr"]

    def test_filenames_as_dict_bad_reader(self):
        """Test loading with filenames dict but one of the readers is bad."""
        from satpy.readers.core.loading import load_readers
        filenames = {
            "viirs_sdr": ["SVI01_npp_d20120225_t1801245_e1802487_b01708_c20120226002130255476_noaa_ops.h5"],
            "__fake__": ["fake.txt"],
        }
        with pytest.raises(ValueError, match=r"(?=.*__fake__)(?!.*viirs)(^No reader.+)"):
            load_readers(filenames=filenames)

    def test_filenames_as_dict_with_reader(self):
        """Test loading from a filenames dict with a single reader specified.

        This can happen in the deprecated Scene behavior of passing a reader
        and a base_dir.

        """
        from satpy.readers.core.loading import load_readers
        filenames = {
            "viirs_sdr": ["SVI01_npp_d20120225_t1801245_e1802487_b01708_c20120226002130255476_noaa_ops.h5"],
        }
        ri = load_readers(reader="viirs_sdr", filenames=filenames)
        assert list(ri.keys()) == ["viirs_sdr"]

    def test_empty_filenames_as_dict(self):
        """Test passing filenames as a dictionary with an empty list of filenames."""
        # only one reader
        from satpy.readers.core.loading import load_readers
        filenames = {
            "viirs_sdr": [],
        }
        with pytest.raises(ValueError, match="No supported files found"):
            load_readers(filenames=filenames)

        # two readers, one is empty
        filenames = {
            "viirs_sdr": ["SVI01_npp_d20120225_t1801245_e1802487_b01708_c20120226002130255476_noaa_ops.h5"],
            "viirs_l1b": [],
        }
        ri = load_readers(filenames)
        assert list(ri.keys()) == ["viirs_sdr"]

    @mock.patch("satpy.readers.core.hrit.HRITFileHandler._get_hd")
    @mock.patch("satpy.readers.seviri_l1b_hrit.HRITMSGFileHandler._get_header")
    @mock.patch("satpy.readers.seviri_l1b_hrit.HRITMSGFileHandler.start_time")
    @mock.patch("satpy.readers.seviri_l1b_hrit.HRITMSGFileHandler.end_time")
    @mock.patch("satpy.readers.seviri_l1b_hrit.HRITMSGPrologueFileHandler.read_prologue")
    @mock.patch("satpy.readers.seviri_l1b_hrit.HRITMSGEpilogueFileHandler.read_epilogue")
    def test_missing_requirements(self, *mocks):
        """Test warnings and exceptions in case of missing requirements."""
        from satpy.readers.core.loading import load_readers

        # Filenames from a single scan
        epi_pro_miss = ["H-000-MSG4__-MSG4________-IR_108___-000006___-201809050900-__"]
        epi_miss = epi_pro_miss + ["H-000-MSG4__-MSG4________-_________-PRO______-201809050900-__"]
        pro_miss = epi_pro_miss + ["H-000-MSG4__-MSG4________-_________-EPI______-201809050900-__"]
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message=r"No handler for reading requirement.*", category=UserWarning)
            for filenames in [epi_miss, pro_miss, epi_pro_miss]:
                with pytest.raises(ValueError, match="No dataset could be loaded.*"):
                    load_readers(reader="seviri_l1b_hrit", filenames=filenames)

        # Filenames from multiple scans
        at_least_one_complete = [
            # 09:00 scan is ok
            "H-000-MSG4__-MSG4________-IR_108___-000006___-201809050900-__",
            "H-000-MSG4__-MSG4________-_________-PRO______-201809050900-__",
            "H-000-MSG4__-MSG4________-_________-EPI______-201809050900-__",
            # 10:00 scan is incomplete
            "H-000-MSG4__-MSG4________-IR_108___-000006___-201809051000-__",
        ]
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message=r"No matching requirement file.*", category=UserWarning)
            try:
                load_readers(filenames=at_least_one_complete, reader="seviri_l1b_hrit")
            except ValueError:
                self.fail("If at least one set of filenames is complete, no "
                          "exception should be raised")

    def test_all_filtered(self):
        """Test behaviour if no file matches the filter parameters."""
        from satpy.readers.core.loading import load_readers
        filenames = {
            "viirs_sdr": ["SVI01_npp_d20120225_t1801245_e1802487_b01708_c20120226002130255476_noaa_ops.h5"],
        }
        filter_params = {"start_time": dt.datetime(1970, 1, 1),
                         "end_time": dt.datetime(1970, 1, 2),
                         "area": None}
        with pytest.raises(ValueError, match="No dataset could be loaded.*"):
            load_readers(filenames=filenames, reader_kwargs={"filter_parameters": filter_params})

    def test_all_filtered_multiple(self):
        """Test behaviour if no file matches the filter parameters."""
        from satpy.readers.core.loading import load_readers
        filenames = {
            "viirs_sdr": ["SVI01_npp_d20120225_t1801245_e1802487_b01708_c20120226002130255476_noaa_ops.h5"],
            "abi_l1b": ["OR_ABI-L1b-RadF-M3C01_G16_s20120561730408_e20120561741175_c20172631741218.nc"],
        }
        filter_params = {"start_time": dt.datetime(1970, 1, 1),
                         "end_time": dt.datetime(1970, 1, 2)}
        with pytest.raises(ValueError, match="No dataset could be loaded."):
            load_readers(filenames=filenames, reader_kwargs={"filter_parameters": filter_params})

    def test_almost_all_filtered(self):
        """Test behaviour if only one reader has datasets."""
        from satpy.readers.core.loading import load_readers
        filenames = {
            "viirs_sdr": ["SVI01_npp_d20120225_t1801245_e1802487_b01708_c20120226002130255476_noaa_ops.h5"],
            "abi_l1b": ["OR_ABI-L1b-RadF-M3C01_G16_s20172631730408_e20172631741175_c20172631741218.nc"],
        }
        filter_params = {"start_time": dt.datetime(2012, 2, 25),
                         "end_time": dt.datetime(2012, 2, 26)}
        # viirs has data that matches the request, abi doesn't
        readers = load_readers(filenames=filenames, reader_kwargs={"filter_parameters": filter_params})
        assert "viirs_sdr" in readers
        # abi_l1b reader was created, but no datasets available
        assert "abi_l1b" in readers
        assert len(list(readers["abi_l1b"].available_dataset_ids)) == 0

    def test_yaml_error_message(self):
        """Test that YAML errors are logged properly."""
        import logging

        import satpy
        from satpy.readers.core.loading import load_readers

        reader_config = "reader:\n"
        reader_config += "  name: nonreader\n"
        reader_config += "  reader: !!python/name:notapackage.notareader.BadClass\n"

        os.mkdir(self._tmp_path / "readers")
        reader_fname = self._tmp_path / "readers" / "nonreader.yaml"
        with open(reader_fname, "w") as fid:
            fid.write(reader_config)

        filenames = ["foo.bar"]
        error_message = "No module named 'notapackage'"

        with self._caplog.at_level(logging.ERROR):
            with satpy.config.set({"config_path": [str(self._tmp_path)]}):
                with pytest.raises(ValueError, match="No supported files found"):
                    _ = load_readers(filenames=filenames, reader="nonreader")
            assert error_message in self._caplog.text


class TestFindFilesAndReaders:
    """Test the find_files_and_readers utility function."""

    def setup_method(self):
        """Wrap HDF5 file handler with our own fake handler."""
        from satpy.readers.viirs_sdr import VIIRSSDRFileHandler
        from satpy.tests.reader_tests.test_viirs_sdr import FakeHDF5FileHandler2

        # http://stackoverflow.com/questions/12219967/how-to-mock-a-base-class-with-python-mock-library
        self.p = mock.patch.object(VIIRSSDRFileHandler, "__bases__", (FakeHDF5FileHandler2,))
        self.fake_handler = self.p.start()
        self.p.is_local = True

    def teardown_method(self):
        """Stop wrapping the HDF5 file handler."""
        self.p.stop()

    def test_reader_name(self, viirs_file):
        """Test with default base_dir and reader specified."""
        ri = find_files_and_readers(reader="viirs_sdr")
        assert list(ri.keys()) == ["viirs_sdr"]
        assert ri["viirs_sdr"] == [viirs_file]

    def test_reader_other_name(self, monkeypatch, tmp_path):
        """Test with default base_dir and reader specified."""
        filename = "S_NWC_CPP_npp_32505_20180204T1114116Z_20180204T1128227Z.nc"
        monkeypatch.chdir(tmp_path)
        # touch the file so it exists on disk
        open(filename, "w").close()

        ri = find_files_and_readers(reader="nwcsaf-pps_nc")
        assert list(ri.keys()) == ["nwcsaf-pps_nc"]
        assert ri["nwcsaf-pps_nc"] == [filename]

    def test_reader_name_matched_start_end_time(self, viirs_file):
        """Test with start and end time matching the filename."""
        ri = find_files_and_readers(reader="viirs_sdr",
                                    start_time=dt.datetime(2012, 2, 25, 18, 0, 0),
                                    end_time=dt.datetime(2012, 2, 25, 19, 0, 0),
                                    )
        assert list(ri.keys()) == ["viirs_sdr"]
        assert ri["viirs_sdr"] == [viirs_file]

    def test_reader_name_matched_start_time(self, viirs_file):
        """Test with start matching the filename.

        Start time in the middle of the file time should still match the file.
        """
        ri = find_files_and_readers(reader="viirs_sdr", start_time=dt.datetime(2012, 2, 25, 18, 1, 30))
        assert list(ri.keys()) == ["viirs_sdr"]
        assert ri["viirs_sdr"] == [viirs_file]

    def test_reader_name_matched_end_time(self, viirs_file):
        """Test with end matching the filename.

        End time in the middle of the file time should still match the file.

        """
        ri = find_files_and_readers(reader="viirs_sdr", end_time=dt.datetime(2012, 2, 25, 18, 1, 30))
        assert list(ri.keys()) == ["viirs_sdr"]
        assert ri["viirs_sdr"] == [viirs_file]

    def test_reader_name_unmatched_start_end_time(self, viirs_file):
        """Test with start and end time matching the filename."""
        with pytest.raises(ValueError, match="No supported files found"):
            find_files_and_readers(reader="viirs_sdr",
                                   start_time=dt.datetime(2012, 2, 26, 18, 0, 0),
                                   end_time=dt.datetime(2012, 2, 26, 19, 0, 0))

    def test_no_parameters(self, viirs_file):
        """Test with no limiting parameters."""
        from satpy.readers.core.grouping import find_files_and_readers

        ri = find_files_and_readers()
        assert list(ri.keys()) == ["viirs_sdr"]
        assert ri["viirs_sdr"] == [viirs_file]

    def test_no_parameters_both_atms_and_viirs(self, viirs_file, atms_file):
        """Test with no limiting parameters when there area both atms and viirs files in the same directory."""
        from satpy.readers.core.grouping import find_files_and_readers

        ri = find_files_and_readers()

        assert "atms_sdr_hdf5" in list(ri.keys())
        assert "viirs_sdr" in list(ri.keys())
        assert ri["atms_sdr_hdf5"] == [atms_file]
        assert ri["viirs_sdr"] == [viirs_file]

    def test_bad_sensor(self):
        """Test bad sensor doesn't find any files."""
        with pytest.raises(ValueError, match="Sensor.* not supported by any readers"):
            find_files_and_readers(sensor="i_dont_exist")

    def test_sensor(self, viirs_file):
        """Test that readers for the current sensor are loaded."""
        # we can't easily know how many readers satpy has that support
        # 'viirs' so we just pass it and hope that this works
        ri = find_files_and_readers(sensor="viirs")
        assert list(ri.keys()) == ["viirs_sdr"]
        assert ri["viirs_sdr"] == [viirs_file]

    def test_sensor_no_files(self):
        """Test that readers for the current sensor are loaded."""
        # we can't easily know how many readers satpy has that support
        # 'viirs' so we just pass it and hope that this works
        with pytest.raises(ValueError, match="No supported files found"):
            find_files_and_readers(sensor="viirs")
        assert find_files_and_readers(sensor="viirs", missing_ok=True) == {}

    def test_reader_load_failed(self):
        """Test that an exception is raised when a reader can't be loaded."""
        import yaml

        from satpy.readers.core.grouping import find_files_and_readers

        # touch the file so it exists on disk
        with mock.patch("yaml.load") as load:
            load.side_effect = yaml.YAMLError("Import problems")
            with pytest.raises(yaml.YAMLError):
                find_files_and_readers(reader="viirs_sdr")

    def test_pending_old_reader_name_mapping(self):
        """Test that requesting pending old reader names raises a warning."""
        from satpy.readers.core.config import PENDING_OLD_READER_NAMES, get_valid_reader_names
        if not PENDING_OLD_READER_NAMES:
            return unittest.skip("Skipping pending deprecated reader tests because "
                                 "no pending deprecated readers.")
        test_reader = sorted(PENDING_OLD_READER_NAMES.keys())[0]
        with pytest.warns(FutureWarning, match=".*will be removed.*"):
            valid_reader_names = get_valid_reader_names([test_reader])
        assert valid_reader_names[0] == PENDING_OLD_READER_NAMES[test_reader]

    def test_old_reader_name_mapping(self):
        """Test that requesting old reader names raises a warning."""
        from satpy.readers.core.config import OLD_READER_NAMES, get_valid_reader_names
        if not OLD_READER_NAMES:
            return pytest.skip("Skipping deprecated reader tests because "
                               "no deprecated readers.")
        test_reader = sorted(OLD_READER_NAMES.keys())[0]
        with pytest.raises(ValueError, match="Reader name .* has been deprecated, use .* instead."):
            get_valid_reader_names([test_reader])


class TestYAMLFiles:
    """Test and analyze the reader configuration files."""

    def test_filename_matches_reader_name(self):
        """Test that every reader filename matches the name in the YAML."""
        import yaml

        class IgnoreLoader(yaml.SafeLoader):
            def _ignore_all_tags(self, tag_suffix, node):
                return tag_suffix + " " + node.value
        IgnoreLoader.add_multi_constructor("", IgnoreLoader._ignore_all_tags)

        from satpy._config import glob_config
        from satpy.readers.core.config import read_reader_config
        for reader_config in glob_config("readers/*.yaml"):
            reader_fn = os.path.basename(reader_config)
            reader_fn_name = os.path.splitext(reader_fn)[0]
            reader_info = read_reader_config([reader_config],
                                             loader=IgnoreLoader)
            assert reader_fn_name == reader_info["name"], \
                "Reader YAML filename doesn't match reader name in the YAML file."

    def test_available_readers(self):
        """Test the 'available_readers' function."""
        from satpy import available_readers

        reader_names = available_readers()
        assert len(reader_names) > 0
        assert isinstance(reader_names[0], str)
        assert "viirs_sdr" in reader_names  # needs h5py
        assert "abi_l1b" in reader_names  # needs netcdf4
        assert reader_names == sorted(reader_names)

        reader_infos = available_readers(as_dict=True)
        assert len(reader_names) == len(reader_infos)
        assert isinstance(reader_infos[0], dict)
        for reader_info in reader_infos:
            assert "name" in reader_info
        assert reader_infos == sorted(reader_infos, key=lambda reader_info: reader_info["name"])

    def test_available_readers_base_loader(self, monkeypatch):
        """Test the 'available_readers' function for yaml loader type BaseLoader."""
        import yaml

        from satpy import available_readers
        from satpy._config import glob_config

        def patched_import_error(name, globals=None, locals=None, fromlist=(), level=0):  # noqa: A002
            if name in ("netcdf4", ):
                raise ImportError(f"Mocked import error {name}")
            return real_import(name, globals=globals, locals=locals, fromlist=fromlist, level=level)

        monkeypatch.delitem(sys.modules, "netcdf4", raising=False)
        monkeypatch.setattr(builtins, "__import__", patched_import_error)

        with pytest.raises(ImportError):
            import netcdf4  # noqa: F401

        reader_names = available_readers(yaml_loader=yaml.BaseLoader)
        assert "abi_l1b" in reader_names  # needs netcdf4
        assert "viirs_l1b" in reader_names
        assert len(reader_names) == len(list(glob_config("readers/*.yaml")))


class TestGroupFiles(unittest.TestCase):
    """Test the 'group_files' utility function."""

    def setUp(self):
        """Set up test filenames to use."""
        input_files = [
            "OR_ABI-L1b-RadC-M3C01_G16_s20171171502203_e20171171504576_c20171171505018.nc",
            "OR_ABI-L1b-RadC-M3C01_G16_s20171171507203_e20171171509576_c20171171510018.nc",
            "OR_ABI-L1b-RadC-M3C01_G16_s20171171512203_e20171171514576_c20171171515017.nc",
            "OR_ABI-L1b-RadC-M3C01_G16_s20171171517203_e20171171519577_c20171171520019.nc",
            "OR_ABI-L1b-RadC-M3C01_G16_s20171171522203_e20171171524576_c20171171525020.nc",
            "OR_ABI-L1b-RadC-M3C01_G16_s20171171527203_e20171171529576_c20171171530017.nc",
            "OR_ABI-L1b-RadC-M3C02_G16_s20171171502203_e20171171504576_c20171171505008.nc",
            "OR_ABI-L1b-RadC-M3C02_G16_s20171171507203_e20171171509576_c20171171510012.nc",
            "OR_ABI-L1b-RadC-M3C02_G16_s20171171512203_e20171171514576_c20171171515007.nc",
            "OR_ABI-L1b-RadC-M3C02_G16_s20171171517203_e20171171519576_c20171171520010.nc",
            "OR_ABI-L1b-RadC-M3C02_G16_s20171171522203_e20171171524576_c20171171525008.nc",
            "OR_ABI-L1b-RadC-M3C02_G16_s20171171527203_e20171171529576_c20171171530008.nc",
        ]
        self.g16_files = input_files
        self.g17_files = [x.replace("G16", "G17") for x in input_files]
        self.noaa20_files = [
            "GITCO_j01_d20180511_t2027292_e2028538_b02476_c20190530192858056873_noac_ops.h5",
            "GITCO_j01_d20180511_t2028550_e2030195_b02476_c20190530192932937427_noac_ops.h5",
            "GITCO_j01_d20180511_t2030208_e2031435_b02476_c20190530192932937427_noac_ops.h5",
            "GITCO_j01_d20180511_t2031447_e2033092_b02476_c20190530192932937427_noac_ops.h5",
            "GITCO_j01_d20180511_t2033105_e2034350_b02476_c20190530192932937427_noac_ops.h5",
            "SVI03_j01_d20180511_t2027292_e2028538_b02476_c20190530190950789763_noac_ops.h5",
            "SVI03_j01_d20180511_t2028550_e2030195_b02476_c20190530192911205765_noac_ops.h5",
            "SVI03_j01_d20180511_t2030208_e2031435_b02476_c20190530192911205765_noac_ops.h5",
            "SVI03_j01_d20180511_t2031447_e2033092_b02476_c20190530192911205765_noac_ops.h5",
            "SVI03_j01_d20180511_t2033105_e2034350_b02476_c20190530192911205765_noac_ops.h5",
            "SVI04_j01_d20180511_t2027292_e2028538_b02476_c20190530190951848958_noac_ops.h5",
            "SVI04_j01_d20180511_t2028550_e2030195_b02476_c20190530192903985164_noac_ops.h5",
            "SVI04_j01_d20180511_t2030208_e2031435_b02476_c20190530192903985164_noac_ops.h5",
            "SVI04_j01_d20180511_t2031447_e2033092_b02476_c20190530192903985164_noac_ops.h5",
            "SVI04_j01_d20180511_t2033105_e2034350_b02476_c20190530192903985164_noac_ops.h5"
        ]
        self.npp_files = [
            "GITCO_npp_d20180511_t1939067_e1940309_b33872_c20190612031740518143_noac_ops.h5",
            "GITCO_npp_d20180511_t1940321_e1941563_b33872_c20190612031740518143_noac_ops.h5",
            "GITCO_npp_d20180511_t1941575_e1943217_b33872_c20190612031740518143_noac_ops.h5",
            "SVI03_npp_d20180511_t1939067_e1940309_b33872_c20190612032009230105_noac_ops.h5",
            "SVI03_npp_d20180511_t1940321_e1941563_b33872_c20190612032009230105_noac_ops.h5",
            "SVI03_npp_d20180511_t1941575_e1943217_b33872_c20190612032009230105_noac_ops.h5",
        ]
        self.unknown_files = [
            "ʌsɔ˙pıʃɐʌuı",
            "no such"]

    def test_no_reader(self):
        """Test that reader does not need to be provided."""
        from satpy.readers.core.grouping import group_files

        # without files it's going to be an empty result
        assert group_files([]) == []
        groups = group_files(self.g16_files)
        assert 6 == len(groups)

    def test_unknown_files(self):
        """Test that error is raised on unknown files."""
        from satpy.readers.core.grouping import group_files
        with pytest.raises(ValueError, match="No matching readers found for these files: .*"):
            group_files(self.unknown_files, "abi_l1b")

    def test_bad_reader(self):
        """Test that reader not existing causes an error."""
        import yaml

        from satpy.readers.core.grouping import group_files

        # touch the file so it exists on disk
        with mock.patch("yaml.load") as load:
            load.side_effect = yaml.YAMLError("Import problems")
            with pytest.raises(yaml.YAMLError):
                group_files([], reader="abi_l1b")

    def test_default_behavior(self):
        """Test the default behavior with the 'abi_l1b' reader."""
        from satpy.readers.core.grouping import group_files
        groups = group_files(self.g16_files, reader="abi_l1b")
        assert 6 == len(groups)
        assert 2 == len(groups[0]["abi_l1b"])

    def test_default_behavior_set(self):
        """Test the default behavior with the 'abi_l1b' reader."""
        from satpy.readers.core.grouping import group_files
        files = set(self.g16_files)
        num_files = len(files)
        groups = group_files(files, reader="abi_l1b")
        # we didn't modify it
        assert len(files) == num_files
        assert 6 == len(groups)
        assert 2 == len(groups[0]["abi_l1b"])

    def test_non_datetime_group_key(self):
        """Test what happens when the start_time isn't used for grouping."""
        from satpy.readers.core.grouping import group_files
        groups = group_files(self.g16_files, reader="abi_l1b", group_keys=("platform_shortname",))
        assert 1 == len(groups)
        assert 12 == len(groups[0]["abi_l1b"])

    def test_large_time_threshold(self):
        """Test what happens when the time threshold holds multiple files."""
        from satpy.readers.core.grouping import group_files
        groups = group_files(self.g16_files, reader="abi_l1b", time_threshold=60*8)
        assert 3 == len(groups)
        assert 4 == len(groups[0]["abi_l1b"])

    def test_two_instruments_files(self):
        """Test the behavior when two instruments files are provided.

        This is undesired from a user point of view since we don't want G16
        and G17 files in the same Scene. Readers (like abi_l1b) are or can be
        configured to have specific group keys for handling these situations.
        Due to that this test forces the fallback group keys of
        ('start_time',).

        """
        from satpy.readers.core.grouping import group_files
        groups = group_files(self.g16_files + self.g17_files, reader="abi_l1b", group_keys=("start_time",))
        assert 6 == len(groups)
        assert 4 == len(groups[0]["abi_l1b"])

    def test_two_instruments_files_split(self):
        """Test the default behavior when two instruments files are provided and split.

        Tell the sorting to include the platform identifier as another field
        to use for grouping.

        """
        from satpy.readers.core.grouping import group_files
        groups = group_files(self.g16_files + self.g17_files, reader="abi_l1b",
                             group_keys=("start_time", "platform_shortname"))
        assert 12 == len(groups)
        assert 2 == len(groups[0]["abi_l1b"])
        # default for abi_l1b should also behave like this
        groups = group_files(self.g16_files + self.g17_files, reader="abi_l1b")
        assert 12 == len(groups)
        assert 2 == len(groups[0]["abi_l1b"])

    def test_viirs_orbits(self):
        """Test a reader that doesn't use 'start_time' for default grouping."""
        from satpy.readers.core.grouping import group_files
        groups = group_files(self.noaa20_files + self.npp_files, reader="viirs_sdr")
        assert 2 == len(groups)
        # the noaa-20 files will be first because the orbit number is smaller
        # 5 granules * 3 file types
        assert 5 * 3 == len(groups[0]["viirs_sdr"])
        # 3 granules * 2 file types
        assert 6 == len(groups[1]["viirs_sdr"])

    def test_viirs_override_keys(self):
        """Test overriding a group keys to add 'start_time'."""
        from satpy.readers.core.grouping import group_files
        groups = group_files(self.noaa20_files + self.npp_files, reader="viirs_sdr",
                             group_keys=("start_time", "orbit", "platform_shortname"))
        assert 8 == len(groups)
        assert 2 == len(groups[0]["viirs_sdr"])  # NPP
        assert 2 == len(groups[1]["viirs_sdr"])  # NPP
        assert 2 == len(groups[2]["viirs_sdr"])  # NPP
        assert 3 == len(groups[3]["viirs_sdr"])  # N20
        assert 3 == len(groups[4]["viirs_sdr"])  # N20
        assert 3 == len(groups[5]["viirs_sdr"])  # N20
        assert 3 == len(groups[6]["viirs_sdr"])  # N20
        assert 3 == len(groups[7]["viirs_sdr"])  # N20

        # Ask for a larger time span with our groups
        groups = group_files(self.noaa20_files + self.npp_files, reader="viirs_sdr",
                             time_threshold=60 * 60 * 2,
                             group_keys=("start_time", "orbit", "platform_shortname"))
        assert 2 == len(groups)
        # NPP is first because it has an earlier time
        # 3 granules * 2 file types
        assert 6 == len(groups[0]["viirs_sdr"])
        # 5 granules * 3 file types
        assert 5 * 3 == len(groups[1]["viirs_sdr"])

    def test_multi_readers(self):
        """Test passing multiple readers."""
        from satpy.readers.core.grouping import group_files
        groups = group_files(
            self.g16_files + self.noaa20_files,
            reader=("abi_l1b", "viirs_sdr"))
        assert len(groups) == 11
        # test that they're grouped together when time threshold is huge and
        # only time is used to group
        groups = group_files(
            self.g16_files + self.noaa20_files,
            reader=("abi_l1b", "viirs_sdr"),
            group_keys=("start_time",),
            time_threshold=10**9)
        assert len(groups) == 1
        # test that a warning is raised when a string is passed (meaning no
        # group keys found in common)
        with pytest.warns(UserWarning, match=".*none of group keys found.*"):
            group_files(
                self.g16_files + self.noaa20_files,
                reader=("abi_l1b", "viirs_sdr"),
                group_keys=("start_time"),
                time_threshold=10**9)

    _filenames_abi_glm = [
        "OR_ABI-L1b-RadF-M6C14_G16_s19000010000000_e19000010005000_c20403662359590.nc",
        "OR_ABI-L1b-RadF-M6C14_G16_s19000010010000_e19000010015000_c20403662359590.nc",
        "OR_ABI-L1b-RadF-M6C14_G16_s19000010020000_e19000010025000_c20403662359590.nc",
        "OR_GLM-L2-GLMF-M3_G16_s19000010000000_e19000010001000_c20403662359590.nc",
        "OR_GLM-L2-GLMF-M3_G16_s19000010001000_e19000010002000_c20403662359590.nc",
        "OR_GLM-L2-GLMF-M3_G16_s19000010002000_e19000010003000_c20403662359590.nc",
        "OR_GLM-L2-GLMF-M3_G16_s19000010003000_e19000010004000_c20403662359590.nc",
        "OR_GLM-L2-GLMF-M3_G16_s19000010004000_e19000010005000_c20403662359590.nc",
        "OR_GLM-L2-GLMF-M3_G16_s19000010005000_e19000010006000_c20403662359590.nc",
        "OR_GLM-L2-GLMF-M3_G16_s19000010006000_e19000010007000_c20403662359590.nc",
        "OR_GLM-L2-GLMF-M3_G16_s19000010007000_e19000010008000_c20403662359590.nc",
        "OR_GLM-L2-GLMF-M3_G16_s19000010008000_e19000010009000_c20403662359590.nc",
        "OR_GLM-L2-GLMF-M3_G16_s19000010009000_e19000010010000_c20403662359590.nc",
        "OR_GLM-L2-GLMF-M3_G16_s19000010010000_e19000010011000_c20403662359590.nc",
        "OR_GLM-L2-GLMF-M3_G16_s19000010011000_e19000010012000_c20403662359590.nc",
        "OR_GLM-L2-GLMF-M3_G16_s19000010012000_e19000010013000_c20403662359590.nc",
        "OR_GLM-L2-GLMF-M3_G16_s19000010013000_e19000010014000_c20403662359590.nc",
        "OR_GLM-L2-GLMF-M3_G16_s19000010014000_e19000010015000_c20403662359590.nc",
        "OR_GLM-L2-GLMF-M3_G16_s19000010015000_e19000010016000_c20403662359590.nc"]

    def test_multi_readers_empty_groups_raises_filenotfounderror(self):
        """Test behaviour on empty groups passing multiple readers.

        Make sure it raises an exception, for there will be groups
        containing GLM but not ABI.
        """
        from satpy.readers.core.grouping import group_files
        with pytest.raises(
                FileNotFoundError, match="when grouping files, group at index 1 "
                "had no files for readers: abi_l1b"):
            group_files(
                self._filenames_abi_glm,
                reader=["abi_l1b", "glm_l2"],
                group_keys=("start_time",),
                time_threshold=35,
                missing="raise")

    def test_multi_readers_empty_groups_missing_skip(self):
        """Verify empty groups are skipped.

        Verify that all groups lacking ABI are skipped, resulting in only
        three groups that are all non-empty for both instruments.
        """
        from satpy.readers.core.grouping import group_files
        groups = group_files(
            self._filenames_abi_glm,
            reader=["abi_l1b", "glm_l2"],
            group_keys=("start_time",),
            time_threshold=35,
            missing="skip")
        assert len(groups) == 2
        for g in groups:
            assert g["abi_l1b"]
            assert g["glm_l2"]

    def test_multi_readers_empty_groups_passed(self):
        """Verify that all groups are there, resulting in some that are empty."""
        from satpy.readers.core.grouping import group_files
        groups = group_files(
            self._filenames_abi_glm,
            reader=["abi_l1b", "glm_l2"],
            group_keys=("start_time",),
            time_threshold=35,
            missing="pass")
        assert len(groups) == 17
        assert not groups[1]["abi_l1b"]  # should be empty
        assert groups[1]["glm_l2"]  # should not be empty

    def test_multi_readers_invalid_parameter(self):
        """Verify that invalid missing parameter raises ValueError."""
        from satpy.readers.core.grouping import group_files
        with pytest.raises(ValueError, match="Invalid value for ``missing`` argument..*"):
            group_files(
                self._filenames_abi_glm,
                reader=["abi_l1b", "glm_l2"],
                group_keys=("start_time",),
                time_threshold=35,
                missing="hopkin green frog")


def _generate_random_string():
    import uuid
    return str(uuid.uuid1())


def _assert_is_open_file_and_close(opened):
    try:
        assert hasattr(opened, "tell")
    finally:
        opened.close()


def _posixify_path(filename):
    drive, driveless_name = os.path.splitdrive(filename)
    return driveless_name.replace("\\", "/")


@pytest.fixture(scope="module")
def random_string():
    """Random string to be used as fake file content."""
    return _generate_random_string()


@pytest.fixture(scope="module")
def local_filename(tmp_path_factory, random_string):
    """Create simple on-disk file."""
    with _local_file(tmp_path_factory, random_string) as local_path:
        yield local_path


@contextlib.contextmanager
def _local_file(tmp_path_factory, filename: str) -> Iterator[Path]:
    tmp_path = tmp_path_factory.mktemp("local_files")
    local_filename = tmp_path / filename
    local_filename.touch()
    yield local_filename


@pytest.fixture(scope="module")
def local_file(local_filename):
    """Open local file with fsspec."""
    import fsspec

    return fsspec.open(local_filename)


@pytest.fixture(scope="module")
def local_filename2(tmp_path_factory):
    """Create a second local file."""
    random_string2 = _generate_random_string()
    with _local_file(tmp_path_factory, random_string2) as local_path:
        yield local_path


@pytest.fixture(scope="module")
def local_zip_file(local_filename2):
    """Create local zip file containing one local file."""
    import zipfile

    zip_name = Path(str(local_filename2) + ".zip")
    zip_file = zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED)
    zip_file.write(local_filename2)
    zip_file.close()
    return zip_name


class TestFSFile:
    """Test the FSFile class."""

    def test_regular_filename_is_returned_with_str(self, random_string):
        """Test that str give the filename."""
        from satpy.readers.core.remote import FSFile
        assert str(FSFile(random_string)) == random_string

    def test_fsfile_with_regular_filename_abides_pathlike(self, random_string):
        """Test that FSFile abides PathLike for regular filenames."""
        from satpy.readers.core.remote import FSFile
        assert os.fspath(FSFile(random_string)) == random_string

    def test_fsfile_with_regular_filename_and_fs_spec_abides_pathlike(self, random_string):
        """Test that FSFile abides PathLike for filename+fs instances."""
        from satpy.readers.core.remote import FSFile
        assert os.fspath(FSFile(random_string, fs=None)) == random_string

    def test_fsfile_with_pathlike(self, local_filename):
        """Test FSFile with path-like object."""
        from pathlib import Path

        from satpy.readers.core.remote import FSFile
        f = FSFile(Path(local_filename))
        assert str(f) == os.fspath(f) == str(local_filename)

    def test_fsfile_with_fs_open_file_abides_pathlike(self, local_file, random_string):
        """Test that FSFile abides PathLike for fsspec OpenFile instances."""
        from satpy.readers.core.remote import FSFile
        assert os.fspath(FSFile(local_file)).endswith(random_string)

    def test_repr_includes_filename(self, local_file, random_string):
        """Test that repr includes the filename."""
        from satpy.readers.core.remote import FSFile
        assert random_string in repr(FSFile(local_file))

    def test_open_regular_file(self, local_filename):
        """Test opening a regular file."""
        from satpy.readers.core.remote import FSFile
        _assert_is_open_file_and_close(FSFile(local_filename).open())

    def test_open_local_fs_file(self, local_file):
        """Test opening a localfs file."""
        from satpy.readers.core.remote import FSFile
        _assert_is_open_file_and_close(FSFile(local_file).open())

    def test_open_zip_fs_regular_filename(self, local_filename2, local_zip_file):
        """Test opening a zipfs with a regular filename provided."""
        from fsspec.implementations.zip import ZipFileSystem

        from satpy.readers.core.remote import FSFile
        zip_fs = ZipFileSystem(local_zip_file)
        file = FSFile(_posixify_path(local_filename2), zip_fs)
        _assert_is_open_file_and_close(file.open())

    def test_open_zip_fs_openfile(self, local_filename2, local_zip_file):
        """Test opening a zipfs openfile."""
        import fsspec

        from satpy.readers.core.remote import FSFile
        open_file = fsspec.open("zip:/" + _posixify_path(local_filename2) + "::file://" + str(local_zip_file))
        file = FSFile(open_file)
        _assert_is_open_file_and_close(file.open())

    def test_sorting_fsfiles(self, local_filename, local_filename2, local_zip_file):
        """Test sorting FSFiles."""
        from fsspec.implementations.zip import ZipFileSystem

        from satpy.readers.core.remote import FSFile
        zip_fs = ZipFileSystem(local_zip_file)
        file1 = FSFile(local_filename2, zip_fs)

        file2 = FSFile(local_filename)

        extra_file = os.path.normpath("/somedir/bla")
        sorted_filenames = [os.fspath(file) for file in sorted([file1, file2, extra_file])]
        expected_filenames = sorted([extra_file, os.fspath(file1), os.fspath(file2)])
        assert sorted_filenames == expected_filenames

    def test_equality(self, local_filename, local_filename2, local_zip_file):
        """Test that FSFile compares equal when it should."""
        from fsspec.implementations.zip import ZipFileSystem

        from satpy.readers.core.remote import FSFile
        zip_fs = ZipFileSystem(local_zip_file)
        assert FSFile(local_filename) == FSFile(local_filename)
        assert (FSFile(local_filename, zip_fs) == FSFile(local_filename, zip_fs))
        assert (FSFile(local_filename, zip_fs) != FSFile(local_filename))
        assert FSFile(local_filename) != FSFile(local_filename2)

    def test_hash(self, local_filename, local_filename2, local_zip_file):
        """Test that FSFile hashing behaves sanely."""
        from fsspec.implementations.cached import CachingFileSystem
        from fsspec.implementations.local import LocalFileSystem
        from fsspec.implementations.zip import ZipFileSystem

        from satpy.readers.core.remote import FSFile

        lfs = LocalFileSystem()
        zfs = ZipFileSystem(local_zip_file)
        cfs = CachingFileSystem(fs=lfs)
        # make sure each name/fs-combi has its own hash
        assert len({hash(FSFile(fn, fs))
                    for fn in {local_filename, local_filename2}
                    for fs in [None, lfs, zfs, cfs]}) == 2 * 4

    def test_fs_property_read(self, local_filename):
        """Test reading the fs property of the class."""
        from satpy.readers.core.remote import FSFile

        fsf = FSFile(local_filename)
        fs = fsf.fs
        assert fs is None

    def test_fs_property_is_read_only(self, local_filename):
        """Test that the fs property of the class is read-only."""
        from satpy.readers.core.remote import FSFile

        fsf = FSFile(local_filename)
        with pytest.raises(AttributeError):
            fsf.fs = "foo"


def test_open_file_or_filename_uses_mode(tmp_path):
    """Test that open_file_or_filename uses provided mode."""
    from satpy.readers.core.remote import FSFile

    filename = tmp_path / "hej"
    with open(filename, mode="wb") as fd:
        fd.write(b"hej")
    fileobj = FSFile(os.fspath(filename))
    res = open_file_or_filename(fileobj, mode="rb").read()
    assert isinstance(res, bytes)


@pytest.fixture(scope="module")
def local_netcdf_filename(tmp_path_factory):
    """Create a simple local NetCDF file."""
    filename = tmp_path_factory.mktemp("fake_netcdfs") / "test.nc"
    ds = xr.Dataset()
    ds.attrs = {
        "attr1": "a",
        "attr2": 2,
    }
    ds["var1"] = xr.DataArray(np.zeros((10, 10), dtype=np.int16), dims=("y", "x"))
    ds.to_netcdf(filename)

    return str(filename)


@pytest.fixture(scope="module")
def local_netcdf_path(local_netcdf_filename):
    """Get Path object pointing to local netcdf file."""
    return Path(local_netcdf_filename)


@pytest.fixture(scope="module")
def local_netcdf_fsspec(local_netcdf_filename):
    """Get fsspec OpenFile object pointing to local netcdf file."""
    import fsspec

    return fsspec.open(local_netcdf_filename)


@pytest.fixture(scope="module")
def local_netcdf_fsfile(local_netcdf_fsspec):
    """Get FSFile object wrapping an fsspec OpenFile pointing to local netcdf file."""
    from satpy.readers.core.remote import FSFile

    return FSFile(local_netcdf_fsspec)


def _open_xarray_netcdf4():
    from functools import partial

    pytest.importorskip("netCDF4")
    return partial(xr.open_dataset, engine="netcdf4")


def _open_xarray_h5netcdf():
    from functools import partial

    pytest.importorskip("h5netcdf")
    return partial(xr.open_dataset, engine="h5netcdf")


def _open_xarray_default():
    pytest.importorskip("netCDF4")
    pytest.importorskip("h5netcdf")
    return xr.open_dataset


@pytest.fixture(scope="module")
def local_hdf5_filename(tmp_path_factory):
    """Create on-disk HDF5 file."""
    import h5py

    filename = tmp_path_factory.mktemp("fake_hdf5s") / "test.h5"
    h = h5py.File(filename, "w")
    h.create_dataset("var1", data=np.zeros((10, 10), dtype=np.int16))
    h.close()

    return str(filename)


@pytest.fixture(scope="module")
def local_hdf5_path(local_hdf5_filename):
    """Get Path object pointing to local HDF5 file."""
    return Path(local_hdf5_filename)


@pytest.fixture(scope="module")
def local_hdf5_fsspec(local_hdf5_filename):
    """Get fsspec OpenFile pointing to local HDF5 file."""
    import fsspec

    return fsspec.open(local_hdf5_filename)


def _open_h5py():
    h5py = pytest.importorskip("h5py")
    return h5py.File


@pytest.mark.parametrize(
    ("file_thing", "create_read_func"),
    [
        (lazy_fixture("local_netcdf_filename"), _open_xarray_default),
        (lazy_fixture("local_netcdf_filename"), _open_xarray_netcdf4),
        (lazy_fixture("local_netcdf_filename"), _open_xarray_h5netcdf),
        (lazy_fixture("local_netcdf_path"), _open_xarray_default),
        (lazy_fixture("local_netcdf_path"), _open_xarray_netcdf4),
        (lazy_fixture("local_netcdf_path"), _open_xarray_h5netcdf),
        (lazy_fixture("local_netcdf_fsspec"), _open_xarray_default),
        (lazy_fixture("local_netcdf_fsspec"), _open_xarray_h5netcdf),
        (lazy_fixture("local_netcdf_fsfile"), _open_xarray_default),
        (lazy_fixture("local_netcdf_fsfile"), _open_xarray_h5netcdf),
        (lazy_fixture("local_hdf5_filename"), _open_h5py),
        (lazy_fixture("local_hdf5_path"), _open_h5py),
        (lazy_fixture("local_hdf5_fsspec"), _open_h5py),
    ],
)
def test_open_file_or_filename(file_thing, create_read_func):
    """Test various combinations of file-like things and opening them with various libraries."""
    from satpy.readers.core.remote import open_file_or_filename

    read_func = create_read_func()
    open_thing = open_file_or_filename(file_thing)
    read_func(open_thing)


@pytest.mark.parametrize("name",
                         ["FSFile",
                          "open_file_or_filename",
                          "group_files",
                          "find_files_and_readers",
                          "read_reader_config",
                          "available_readers",
                          "get_valid_reader_names",
                          "OLD_READER_NAMES",
                          "PENDING_OLD_READER_NAMES",
                          "load_readers",
                          "load_reader",
                          ]
                         )
def test_init_import_warns(name):
    """Test that importing non-reader functions from __init__.py issue a warning."""
    from satpy import readers

    with pytest.warns(UserWarning, match=".*has been moved.*"):
        _ = getattr(readers, name)
