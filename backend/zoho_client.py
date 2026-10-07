import os
import time
from typing import Any

import httpx
from .config import load_project_environment

load_project_environment()


class ZohoCRMClient:

    def __init__(self):

        self.client_id = os.getenv(
            "ZOHO_CLIENT_ID",
            ""
        )

        self.client_secret = os.getenv(
            "ZOHO_CLIENT_SECRET",
            ""
        )

        self.refresh_token = os.getenv(
            "ZOHO_REFRESH_TOKEN",
            ""
        )

        self.accounts_url = os.getenv(
            "ZOHO_ACCOUNTS_URL",
            "https://accounts.zoho.in"
        ).rstrip("/")

        self.api_base = os.getenv(
            "ZOHO_API_BASE",
            "https://www.zohoapis.in"
        ).rstrip("/")

        self.access_token = None
        self.expires_at = 0


    def configured(self):

        return all([
            self.client_id,
            self.client_secret,
            self.refresh_token
        ])


    async def get_access_token(
        self,
        force_refresh=False
    ):

        # Existing token still valid
        if (
            not force_refresh
            and self.access_token
            and time.time() < self.expires_at - 60
        ):
            return self.access_token


        if not self.configured():

            raise RuntimeError(
                "Zoho OAuth credentials are missing. "
                "Check your .env file."
            )


        params = {

            "refresh_token":
                self.refresh_token,

            "client_id":
                self.client_id,

            "client_secret":
                self.client_secret,

            "grant_type":
                "refresh_token"
        }


        async with httpx.AsyncClient(
            timeout=30
        ) as client:

            response = await client.post(

                f"{self.accounts_url}"
                "/oauth/v2/token",

                params=params
            )


        if response.is_error:

            raise RuntimeError(

                f"Zoho OAuth failed "
                f"({response.status_code}): "
                f"{response.text}"
            )


        data = response.json()

        token = data.get(
            "access_token"
        )


        if not token:

            raise RuntimeError(
                f"Zoho did not return "
                f"an access token: {data}"
            )


        self.access_token = token

        self.expires_at = (
            time.time()
            + int(
                data.get(
                    "expires_in",
                    3600
                )
            )
        )


        # Zoho can return the correct
        # API domain for the organization.

        api_domain = data.get(
            "api_domain"
        )

        if api_domain:

            self.api_base = (
                api_domain.rstrip("/")
            )


        return token


    async def request(
        self,
        method: str,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None
    ):

        token = await self.get_access_token()


        headers = {

            "Authorization":
                f"Zoho-oauthtoken {token}",

            "Content-Type":
                "application/json"
        }


        async with httpx.AsyncClient(
            timeout=30
        ) as client:

            response = await client.request(

                method,

                f"{self.api_base}"
                f"{endpoint}",

                headers=headers,

                params=params,

                json=json
            )


            # Token expired → refresh once

            if response.status_code == 401:

                token = await self.get_access_token(
                    force_refresh=True
                )

                headers["Authorization"] = (
                    f"Zoho-oauthtoken {token}"
                )


                response = await client.request(

                    method,

                    f"{self.api_base}"
                    f"{endpoint}",

                    headers=headers,

                    params=params,

                    json=json
                )


        if response.is_error:

            raise RuntimeError(

                f"Zoho CRM API failed "
                f"({response.status_code}): "
                f"{response.text}"
            )


        return response.json()


    # =====================================
    # GET LEADS
    # =====================================

    async def get_leads(
        self,
        page: int = 1,
        per_page: int = 10
    ):

        return await self.request(

            "GET",

            "/crm/v8/Leads",

            params={

                "page": page,

                "per_page":
                    min(per_page, 200)
            }
        )


    # =====================================
    # CREATE LEAD
    # =====================================

    async def create_lead(

        self,
        last_name: str,
        company: str,
        email: str | None = None,
        first_name: str | None = None
    ):

        record = {

            "Last_Name":
                last_name,

            "Company":
                company
        }


        if email:

            record["Email"] = email


        if first_name:

            record["First_Name"] = first_name


        return await self.request(

            "POST",

            "/crm/v8/Leads",

            json={

                "data": [
                    record
                ]
            }
        )


    # =====================================
    # UPDATE LEAD
    # =====================================

    async def update_lead(

        self,
        lead_id: str,
        fields: dict[str, Any]
    ):

        return await self.request(

            "PUT",

            f"/crm/v8/Leads/{lead_id}",

            json={

                "data": [
                    fields
                ]
            }
        )


    # =====================================
    # SEARCH LEAD
    # =====================================

    async def search_leads(

        self,
        email: str
    ):

        safe_email = (
            email.replace(
                "'",
                "''"
            )
        )


        query = (

            "select "
            "id,"
            "First_Name,"
            "Last_Name,"
            "Full_Name,"
            "Email,"
            "Company,"
            "Lead_Status,"
            "Created_Time "

            "from Leads "

            f"where Email = "
            f"'{safe_email}' "

            "limit 20"
        )


        return await self.request(

            "POST",

            "/crm/v8/coql",

            json={

                "select_query":
                    query
            }
        )


    # =====================================
    # GET CONTACTS
    # =====================================

    async def get_contacts(

        self,
        page: int = 1,
        per_page: int = 10
    ):

        return await self.request(

            "GET",

            "/crm/v8/Contacts",

            params={

                "page": page,

                "per_page":
                    min(per_page, 200)
            }
        )