import logging
from datetime import datetime
from itertools import groupby

from pilotecmwf_pp_starter import CONFIG
from pilotecmwf_pp_starter.domain.processing import Processing


class PrepProcessing:

    def aggregate_s3_objects(self, objects):
        obj_in_s3 = []

        for item in objects.get("Contents", []):
            key = item.get("Key")
            forecast_ref_time_str = f"{datetime.now().year}{key[3:11]}"
            forecast_ref_time = datetime.strptime(forecast_ref_time_str, "%Y%m%d%H%M")
            valid_time_str = f"{datetime.now().year}{key[11:18]}"
            valid_time_obj = datetime.strptime(valid_time_str, "%Y%m%d%H%M")

            step = (
                0
                # there are two steps 0 (one const and one init data)
                # condition below to differentiate them
                if valid_time_obj.minute == 1
                else int((valid_time_obj - forecast_ref_time).total_seconds() / 3600)
            )
            obj_in_s3.append(
                {
                    "key": key,
                    "forecast_ref_time": forecast_ref_time,
                    "step": step,
                    "processed": "N",
                }
            )
        obj_in_s3.sort(key=lambda x: x["forecast_ref_time"])
        return obj_in_s3

    def launch_pre_processing(self, objects):
        obj_in_s3 = self.aggregate_s3_objects(objects)
        for fcst_ref_time, group in groupby(
            obj_in_s3, key=lambda x: x["forecast_ref_time"]
        ):
            files_per_run = list(group)
            step_zero = [file for file in files_per_run if file["step"] == 0]
            steps = [file["step"] for file in files_per_run]

            if len(step_zero) < 2:
                message = (
                    f"Currently only {len(step_zero)} step=0 files are available. "
                    "Waiting for these before processing."
                )
                logging.info(message)
                continue

            for file in files_per_run:
                step = file["step"]

                if (
                    step - CONFIG.main.time_settings.tstart
                ) % CONFIG.main.time_settings.tincr != 0:
                    continue

                prev_step = step - CONFIG.main.time_settings.tincr
                if prev_step not in steps or file["processed"] == "Y":
                    logging.info(
                        f"Not launching Pre-Processing for timestep {step}: "
                        f"prev_step in steps: {prev_step in steps}, "
                        f"processed: {file['processed'] == 'Y'}"
                    )
                    continue

                logging.info(f"Launching Pre-Processing for timestep {step}")
                if prev_step == 0:
                    Processing().process(step_zero + [file])
                else:
                    prev_file = next(
                        (item for item in files_per_run if item["step"] == prev_step),
                        None,
                    )
                    if prev_file:
                        Processing().process(step_zero + [prev_file, file])
                file["processed"] = "Y"