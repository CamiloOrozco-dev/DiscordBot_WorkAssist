"""
Cliente para interactuar con la API de Jibble (v2.0)
"""
import aiohttp
import time
from typing import Optional, List, Dict
from .config import JIBBLE_CLIENT_ID, JIBBLE_CLIENT_SECRET, JIBBLE_ORG_ID

class JibbleAPI:
    """Cliente para interactuar con la API de Jibble"""

    def __init__(self):
        self.auth_url = "https://identity.prod.jibble.io/connect/token"
        # URL base por defecto para v1 (aunque los métodos usan URLs de servicio específicas)
        self.api_url = "https://workspace.prod.jibble.io/v1"
        self.client_id = JIBBLE_CLIENT_ID
        self.client_secret = JIBBLE_CLIENT_SECRET
        self.org_id = JIBBLE_ORG_ID
        self.access_token = None
        self.token_expiry = 0
        self._session: Optional[aiohttp.ClientSession] = None

    async def _handle_response(self, response: aiohttp.ClientResponse):
        """Manejar respuestas de la API y registrar errores detallados"""
        self.last_error_code = ""
        self.last_status = response.status
        if response.status >= 400:
            try:
                error_data = await response.json()
                self.last_error_code = error_data.get("error", {}).get("code", "")
            except:
                error_data = await response.text()
            print(f"⚠️ Jibble API Error {response.status}: {error_data}")
            return None
        return await response.json()

    async def _get_session(self) -> aiohttp.ClientSession:
        """Obtener o crear la sesión de aiohttp"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def _get_access_token(self) -> Optional[str]:
        """Obtener token de acceso usando OAuth2 client credentials flow"""
        if self.access_token and time.time() < self.token_expiry:
            return self.access_token
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }

        session = await self._get_session()
        try:
            async with session.post(self.auth_url, data=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    self.access_token = data["access_token"]
                    self.token_expiry = time.time() + data.get("expires_in", 3600) - 60
                    return self.access_token
                else:
                    error_body = await response.text()
                    print(f"❌ Error de autenticación Jibble: {response.status} - {error_body}")
                    return None
        except Exception as e:
            print(f"❌ Excepción en autenticación: {str(e)}")
            return None

    async def create_time_entry(self, person_id: str, activity_id: Optional[str], 
                               project_id: Optional[str], note: str, 
                               type: str = "In") -> Optional[Dict]:
        """Crear una entrada de tiempo en Jibble v1"""
        token = await self._get_access_token()
        if not token:
            return None

        # Mapeo de tipos para Jibble v1 (IMPORTANTE: Jibble devuelve strings pero ESPERA strings numéricos):
        # Jibble API DEVUELVE: "In", "Out", "StartBreak", "EndBreak" (strings descriptivos)
        # Jibble API ESPERA: "In" (string), "1", "2", "0" (strings numéricos para Out, StartBreak, EndBreak)
        type_mapping = {
            "In": "In",           # In se mantiene como string
            "Out": "1",           # Out = "1" (string)
            "StartBreak": "2",    # StartBreak = "2" (string)
            "EndBreak": "0",      # EndBreak = "0" (string)
            "Break": "2"          # Alias para StartBreak
        }
        
        # Obtener el valor de mapeo
        final_type = type_mapping.get(type, type)

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        payload = {
            "personId": person_id,
            "type": final_type,
            "note": note,
            "time": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            "clientType": "Web",
            "platform": {
                "clientVersion": "2.1",
                "os": "Discord",
                "deviceModel": "Desktop",
                "deviceName": "Discord-Bot"
            }
        }

        if activity_id:
            payload["activityId"] = activity_id
        if project_id:
            payload["projectId"] = project_id

        session = await self._get_session()
        try:
            # Endpoint v1 para Time Entries
            url = "https://time-tracking.prod.jibble.io/v1/TimeEntries"
            
            async with session.post(
                url,
                json=payload,
                headers=headers
            ) as response:
                result = await self._handle_response(response)
                if not result:
                    if response.status >= 500:
                        print(f"🔥 Jibble API Server Error {response.status}: Posible caída del servicio de Jibble.")
                    elif response.status != 201:
                        body = await response.text()
                        print(f"❌ Jibble API Error {response.status} ({type} -> {final_type}): {body}")
                return result
        except Exception as e:
            print(f"❌ Error al crear entrada en Jibble: {str(e)}")
            return None

    async def get_project_by_name(self, name: str) -> Optional[str]:
        """Buscar el ID de un proyecto por su nombre"""
        projects = await self.get_projects()
        if not projects:
            return None
        
        for project in projects:
            if project.get("name").lower() == name.lower():
                return project.get("id")
        return None

    async def get_person_by_email(self, email: str) -> Optional[str]:
        """Obtener personId de Jibble basado en el email usando v1 People"""
        token = await self._get_access_token()
        if not token:
            return None

        headers = {"Authorization": f"Bearer {token}"}
        params = {"$filter": f"email eq '{email}'"}
        
        session = await self._get_session()
        try:
            url = "https://workspace.prod.jibble.io/v1/People"
            async with session.get(url, headers=headers, params=params) as response:
                data = await self._handle_response(response)
                if data and "value" in data and len(data["value"]) > 0:
                    return data["value"][0]["id"]
                return None
        except Exception as e:
            print(f"❌ Error al buscar persona por email: {str(e)}")
            return None

    async def get_people(self) -> Optional[List[Dict]]:
        """Obtener lista de todas las personas en la organización usando v1 People"""
        token = await self._get_access_token()
        if not token:
            return None

        headers = {"Authorization": f"Bearer {token}"}
        session = await self._get_session()
        try:
            url = "https://workspace.prod.jibble.io/v1/People"
            async with session.get(url, headers=headers) as response:
                data = await self._handle_response(response)
                if data and "value" in data:
                    return data["value"]
                return None
        except Exception as e:
            print(f"❌ Error al obtener lista de personas: {str(e)}")
            return None

    async def get_projects(self) -> Optional[List[Dict]]:
        """Obtener lista de proyectos de la organización usando v1 Projects"""
        token = await self._get_access_token()
        if not token:
            return None

        headers = {"Authorization": f"Bearer {token}"}
        session = await self._get_session()
        try:
            url = "https://workspace.prod.jibble.io/v1/Projects"
            async with session.get(url, headers=headers) as response:
                data = await self._handle_response(response)
                if data and "value" in data:
                    return data["value"]
                return None
        except Exception as e:
            print(f"❌ Error al obtener lista de proyectos: {str(e)}")
            return None

    async def get_activities(self) -> Optional[List[Dict]]:
        """Obtener lista de actividades de la organización usando v1 Activities"""
        token = await self._get_access_token()
        if not token:
            return None

        headers = {"Authorization": f"Bearer {token}"}
        session = await self._get_session()
        try:
            url = "https://workspace.prod.jibble.io/v1/Activities"
            async with session.get(url, headers=headers) as response:
                data = await self._handle_response(response)
                if data and "value" in data:
                    return data["value"]
                return None
        except Exception as e:
            print(f"❌ Error al obtener lista de actividades: {str(e)}")
            return None

    async def get_time_entries(self, person_id: str, limit: int = 5) -> Optional[List[Dict]]:
        """Obtener las últimas entradas de tiempo de una persona"""
        token = await self._get_access_token()
        if not token:
            return None

        headers = {"Authorization": f"Bearer {token}"}
        # Filtrar por personId y ordenar por tiempo descendente
        # GUID en OData no debe tener comillas simples
        params = {
            "$filter": f"personId eq {person_id}",
            "$orderby": "time desc",
            "$top": limit
        }
        
        session = await self._get_session()
        try:
            url = "https://time-tracking.prod.jibble.io/v1/TimeEntries"
            async with session.get(url, headers=headers, params=params) as response:
                data = await self._handle_response(response)
                if data and "value" in data:
                    return data["value"]
                return None
        except Exception as e:
            print(f"❌ Error al obtener entradas de tiempo: {str(e)}")
            return None

    async def close(self):
        """Cerrar la sesión de aiohttp"""
        if self._session and not self._session.closed:
            await self._session.close()
