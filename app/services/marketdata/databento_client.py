from __future__ import annotations

import pathlib
from datetime import date
from typing import Iterable, List

import databento as db
import pandas as pd


DATASET = "GLBX.MDP3"
SCHEMA = "ohlcv-1d"
STYPE_IN = "raw_symbol"


class DatabentoClient:
    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("DATABENTO_APIKEY is required")
        self.client = db.Historical(api_key)

    def estimate_cost(self, symbols: Iterable[str], start: date, end: date) -> float:
        symbol_list = ",".join(symbols)
        cost = self.client.metadata.get_cost(
            dataset=DATASET,
            schema=SCHEMA,
            symbols=symbol_list,
            start=start.isoformat(),
            end=end.isoformat(),
        )
        return float(cost)

    def submit_batch_job(self, symbols: Iterable[str], start: date, end: date) -> str:
        symbol_list = ",".join(symbols)
        job = self.client.batch.submit_job(
            dataset=DATASET,
            schema=SCHEMA,
            symbols=symbol_list,
            start=start.isoformat(),
            end=end.isoformat(),
            split_duration="day",
            split_symbols=True,
            stype_in=STYPE_IN,
        )
        return job["id"]

    def list_jobs(self, status: str) -> List[str]:
        return [job["id"] for job in self.client.batch.list_jobs(status)]

    def download_job(self, job_id: str, output_dir: pathlib.Path) -> List[pathlib.Path]:
        files = self.client.batch.download(job_id=job_id, output_dir=output_dir)
        return [pathlib.Path(path) for path in files]

    def get_range(self, symbols: Iterable[str], start: date, end: date) -> pd.DataFrame:
        symbol_list = ",".join(symbols)
        store = self.client.timeseries.get_range(
            dataset=DATASET,
            schema=SCHEMA,
            symbols=symbol_list,
            start=start.isoformat(),
            end=end.isoformat(),
            stype_in=STYPE_IN,
        )
        return store.to_df()


def df_from_dbn_files(files: Iterable[pathlib.Path]) -> pd.DataFrame:
    frames: List[pd.DataFrame] = []
    for file in sorted(files):
        if not file.name.endswith(".dbn.zst"):
            continue
        store = db.DBNStore.from_file(file)
        frames.append(store.to_df())
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)
