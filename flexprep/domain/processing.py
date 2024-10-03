import logging
import os
import tempfile
import typing
from datetime import datetime as dt

import meteodatalab.operators.flexpart as flx
from meteodatalab import config, data_source, grib_decoder, metadata

from flexprep.domain.db_utils import DB
from flexprep.domain.flexpart_utils import CONSTANTS, INPUT_FIELDS, prepare_output
from flexprep.domain.s3_utils import S3client
from flexprep.domain.validation_utils import validate_dataset

logger = logging.getLogger(__name__)


class Processing:
    FileObject = dict[str, typing.Any]

    def __init__(self) -> None:
        self.s3_client = S3client()

    def process(self, file_objs: list[FileObject]) -> None:
        result = self._sort_and_download_files(file_objs)
        if result is None:
            logger.exception("Failed to sort and download files.")
            raise

        temp_files, to_process, prev_file = result

        ds_in = self._load_and_validate_data(temp_files, to_process, prev_file)
        if ds_in is None:
            logger.exception("Failed to load and validate data.")
            raise

        ds_out = self._apply_flexpart(ds_in)
        self._save_output(
            ds_out,
            to_process["forecast_ref_time"],
            int(to_process["step"]),
            to_process["row_id"],
        )

    def _sort_and_download_files(
        self, file_objs: list[FileObject]
    ) -> tuple[list[str], FileObject, FileObject] | None:
        """Sort file objects, validate, and select files for processing."""
        try:
            sorted_files = sorted(file_objs, key=lambda x: int(x["step"]), reverse=True)
            if len(sorted_files) < 3:
                raise ValueError("Not enough files for pre-processing")

            to_process = sorted_files[0]
            prev_file = sorted_files[1]

            init_files = (
                sorted_files[2:4] if int(prev_file["step"]) == 0 else sorted_files[2:4]
            )
            files_to_download = [to_process, prev_file] + init_files

            tempfiles = self._download_files(files_to_download)
            return tempfiles, to_process, prev_file

        except Exception as e:
            logger.exception(f"Sorting and validation failed: {e}")
            return None

    def _download_files(self, files_to_download: list[FileObject]) -> list[str]:
        """Download files from S3 based on the file objects."""
        try:
            return [
                self.s3_client.download_file(file_obj) for file_obj in files_to_download
            ]
        except Exception as e:
            logger.exception(f"File download failed: {e}")
            raise RuntimeError("An error occurred while downloading files.") from e

    def _load_and_validate_data(
        self, temp_files: list[str], to_process: FileObject, prev_file: FileObject
    ) -> typing.Any:
        """Load and validate data from downloaded files."""
        request = {"param": list(CONSTANTS | INPUT_FIELDS)}
        try:
            with config.set_values(data_scope="ifs"):
                source = data_source.FileDataSource(datafiles=temp_files)
                ds_in = grib_decoder.load(source, request)
                validate_dataset(
                    ds_in,
                    request["param"],
                    to_process["forecast_ref_time"],
                    int(to_process["step"]),
                    int(prev_file["step"]),
                )
                ds_in |= metadata.extract_pv(ds_in["u"].message)

            return ds_in

        except Exception as e:
            logger.exception(f"Data loading and validation failed: {e}")
            raise

        finally:
            # Ensure temporary files are cleaned up
            for temp_file in temp_files:
                os.unlink(temp_file)

    def _apply_flexpart(self, ds_in: typing.Any) -> typing.Any:
        """Apply flexpart pre-processing and return processed data structure."""
        ds_out = flx.fflexpart(ds_in)
        prepare_output(ds_out, ds_in, INPUT_FIELDS, CONSTANTS)
        return ds_out

    def _save_output(
        self,
        ds_out: typing.Any,
        forecast_ref_time: dt,
        step_to_process: int,
        row_id: int,
    ) -> None:
        """Save processed data to a temporary file and upload to output-S3."""
        forecast_ref_time_str = forecast_ref_time.strftime("%Y%m%d%H%M")

        try:
            key = f"output_dispf{forecast_ref_time_str}{step_to_process}"
            with tempfile.NamedTemporaryFile(
                suffix=key,
            ) as output_file:
                # Write data to the temporary file
                with open(output_file.name, "wb") as fout:
                    for name, field in ds_out.items():
                        if field.attrs.get("v_coord") == "hybrid":
                            logger.info(f"Writing GRIB fields to {output_file.name}")
                            grib_decoder.save(field, fout)

                    # Upload the file to S3
                    S3client().upload_file(output_file.name, key=key)

            # Mark the item as processed if everything was successful
            DB().update_item_as_processed(row_id)

        except Exception as e:
            logger.exception(f"Failed to save or upload output file: {e}")
            raise
