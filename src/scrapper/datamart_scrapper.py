from var.config import DatamartScrapperConfig, Slugs

import requests
import pandas as pd
import time


class DatamartProcessor:
    def __init__(self):
        self.config = DatamartScrapperConfig.config
        self.slug_config = Slugs.slugs
        # Amount of time the processor will wait until it tries to pull the slug ID again
        self.retry_delay = self.slug_config.get('retry_delay')

    def scrap_slug(self, slug_id):
        slug_data = self.slug_config.get(slug_id)

        if slug_data is None:
            msg = f'Failed to find Slug ID: {slug_id} in config class "Slugs"'
            raise ValueError(f'Failed to find Slug ID: {slug_id} in config class "Slugs"')
        else:
            msg = f'Found Slug ID: {slug_id}'
            print(msg)
        url = self.create_datamart_url(slug_id)
        results = self.pull_datamart(url, repeat=True, retry_delay=self.retry_delay, slug_id=slug_id)
        print(url)
        print(results)


    def create_datamart_url(self, slug_id, report_section='Summary', pull_date=None, end_date=None, operator=None):
        """
        Constructs a URL for accessing data from a datamart.

        The function builds a URL by appending query parameters for date filtering
        based on the provided arguments.
        """
        base_url = self.config.get('datamart_base_url')

        url = f"{base_url}{slug_id}/{report_section}"

        if operator or pull_date or end_date:
            url += "?q=report_date"
            operators = {'after': '>', 'before': '<', 'equals': '='}
            url += operators.get(operator, "=")

        if pull_date or end_date:
            url += str(pull_date) if pull_date else str(end_date)
            if pull_date and end_date:
                url += f":{end_date}"
        else:
            url += "2020-01-01"

        return url

    def pull_datamart(self, url, repeat=False, retry_delay=10, slug_id=None):
        """
        Continuously fetch data from the API using the given URL until 'results' are found in the response.

        :param url: The API URL to fetch data from.
        :type url: str
        :param repeat: Flag to decide between a single pull or repeated pulls until 'results' are found. Defaults to False.
        :type repeat: bool
        :param retry_delay: Delay in seconds between retries if 'results' are not found. Defaults to 10 seconds.
        :type retry_delay: int
        :return: DataFrame with fetched data, or None if an error occurs.
        :rtype: pd.DataFrame or None

        The function performs an HTTP GET request to the specified URL. If `repeat` is True,
        it keeps making requests until the 'results' field is present in the response.
        If `repeat` is False, it makes a single request. The function returns None if an HTTP
        request fails or if 'results' is never found in the response.
        """
        if slug_id:
            msg = f'Repeating Pull - Slug ID:{slug_id}'
        else:
            msg = 'Repeating Pull'
        while True:
            try:
                response = requests.get(url)
                response.raise_for_status()
                data = response.json()

                if "results" in data:
                    return pd.DataFrame(data["results"])
                elif not repeat:
                    return None
                else:
                    print(msg)
                    time.sleep(retry_delay)

            except requests.HTTPError as http_err:
                print(f"HTTP error occurred: {http_err}")
                return None
            except requests.RequestException as req_err:
                print(f"Request error occurred: {req_err}")
                return None
            except ValueError as val_err:
                print(f"Value error: {val_err}")
                return None
            except Exception as e:
                print(f"An error occurred: {e}")
                return None

        return None