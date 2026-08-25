from unittest.mock import patch, Mock

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.api_client import APIClient


def test_api_client_success():

    mock_response = Mock()

    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data":[
            {
                "id":"LI001",
                "name":"Test User"
            }
        ]
    }

    with patch(
        "src.api_client.requests.Session.get", 
        return_value=mock_response
    ):

        client = APIClient()

        result = client.get("/leads")

        assert "data" in result

        client.close()