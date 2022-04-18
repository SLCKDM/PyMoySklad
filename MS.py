"""
Пакет для работы с API МойСклад
MS doc: https://dev.moysklad.ru/doc/api/remap/1.2/documents/
Пока что в данном пакете реализованы классы для
работы со следующими сущностями:
  - Заказ;
  - перемещение;
  - оприходование
Работа с ними разделяется на оперирование с единчными
сущностми и на оперирование со списком сущностей.
Методы работы с единичными сущностями:
  - Получение позиций сущности;
  - получение доп. аттрибуты;
  - получение сырые данные;
  - удаление сущности;
  - внесение в сущность изменений

TODO: Добавить сущности: списания, товаров, отгрузок, приемок, счетов поставщиков
"""

from session import session
from typing import Dict, List
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

session = requests.Session()
retry = Retry(connect=4, backoff_factor=1)
adapter = HTTPAdapter(max_retries=retry)
session.mount('http://', adapter)
session.mount('https://', adapter)

class MoySkladConnector:
    MS_BASE_URL = 'https://online.moysklad.ru/api/remap/1.2'

    def __init__(self, token:str):
        self.token=token
        self.ms_headers = {
            "Authorization": self.token,
            "Content-Type": "application/json",
            "Connection": "keep-alive"
        }

class MSStocks:
    def __init__(self, msconnector: MoySkladConnector):
        self.MS_STOCKS_BASE_URL = f"{msconnector.MS_BASE_URL}/report/stock"
        self.headers = msconnector.ms_headers

    def get_stocks(self,
                   limit:int=None,
                   offset:int=None,
                   filters:str=None,
                   expand:str=None,
                   groupBy:str='variant'
                   ) -> dict:
        """ Получить остатки
        https://dev.moysklad.ru/doc/api/remap/1.2/reports/#otchety-otchet-ostatki-poluchit-ostatki

        Args:
            limit (int, optional): Максимальное количество сущностей для извлечения. Defaults to None.
            offset (int, optional): Отступ в выдаваемом списке сущностей. Defaults to None.
            filters (str, optional): фильтры. Defaults to None.
            groupBy (str, optional): тип, по которому нужно сгруппировать выдачу (`variant`,`product`,`consignment`). Defaults to 'variant'.

        Returns:
            dict: _description_
        """
        url = f'{self.MS_STOCKS_BASE_URL}/all'
        payload = {
            "limit":limit,
            "offset":offset,
            "groupBy":groupBy,
            "filter":filters,
            "expand":expand
        }
        return session.get(url=url, headers=self.headers, params=payload).json()

    def get_stocks_bystore(self,
                           limit:int=None,
                           offset:int=None,
                           filters:str=None,
                           expand:str=None,
                           groupBy:str='variant'
                           ) -> dict:
        """ Остатки по складам
        https://dev.moysklad.ru/doc/api/remap/1.2/reports/#otchety-otchet-ostatki-poluchit-ostatki-po-skladam

        Args:
            limit (int, optional): Максимальное количество сущностей для извлечения. Defaults to None.
            offset (int, optional): Отступ в выдаваемом списке сущностей. Defaults to None.
            filters (str, optional): фильтры. Defaults to None.
            groupBy (str, optional): тип, по которому нужно сгруппировать выдачу ('product', 'variant', 'consignment'). Defaults to 'variant'.

        Returns:
            dict: _description_
        """
        url = f'{self.MS_STOCKS_BASE_URL}/bystore'
        payload = {
            "limit":limit,
            "offset":offset,
            "groupBy":groupBy,
            "filter":filters,
            "expand":expand
        }
        return session.get(url=url, headers=self.headers, params=payload).json()

    def get_current_stocks(self,
                           mode:str='all',
                           stockType:str='stock',
                           filters:str=None,
                           expand:str=None
                           ) -> dict:
        """ Текущие остатки
        https://dev.moysklad.ru/doc/api/remap/1.2/reports/#otchety-otchet-ostatki-tekuschie-ostatki

        Args:
            mode (str, optional): `all` или `bystore`. Defaults to 'all'.
            stockType (str, optional): `stock`, `freeStock`или `quantity`. Defaults to 'stock'.
            filters (str, optional): `assortmentId` и `storeId`. Defaults to None.

        Returns:
            dict: _description_
        """
        url = f'{self.MS_STOCKS_BASE_URL}/{mode}/current'
        payload = {
            "stockType":stockType,
            "filter":filters,
            "expand":expand
        }
        return session.get(url=url, headers=self.headers, params=payload).json()

class MSAssortment:

    def __init__(self, msconnector: MoySkladConnector):
        self.assortment_url = f"{msconnector.MS_BASE_URL}/entity/assortment"
        self.headers = msconnector.ms_headers

    def get(self,
            filters:str=None,
            expand:str=None,
            next_href=None
            ) -> Dict:
        """ Возвращает товары с МС

        Args:
            filters (str, optional): фильтры. Defaults to None.
            next_href (_type_, optional): следующая ссылка для рекурсии. Defaults to None.

        Returns:
            dict: товары, соответствующие запросу
        """
        payload = {
            "filter": filters,
            "expand": expand
            }
        response = session.get(url=next_href or self.assortment_url, headers=self.headers, params=payload).json()
        result = response['rows']
        if response['meta'].get('nextHref'):
            result.extend(self.get(next_href=response['meta']['nextHref'])['rows'])
        return result

class Position:
    """ Позиции товаров в документе """
    def __init__(self,
                 msconnector: MoySkladConnector,
                 url:str,
                 entity_id:str=None,
                 pos_id:str=None,
                 raw_data:dict=None
                ):
        self.headers = msconnector.ms_headers
        self.id = pos_id or raw_data['id']
        self.entity_position_url = f"{url}/positions/{self.id}"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__} <id: {self.id}>"

    def __str__(self) -> str:
        return f"{self.__class__.__name__} <id: {self.id}>"

    @property
    def raw_data(self):
        payload = {"expand" : "assortment"}
        return session.get(url=self.entity_position_url,
                           headers=self.headers,
                           params=payload).json()

    @property
    def assortment(self):
        return self.raw_data['assortment']

#! <---------- Single entity ------------------------------------------------->

class Entity:
    """ Абстрактный класс сущностей (Перемещение, заказ и т.д.) """

    def __init__(self, msconnector: MoySkladConnector, id:str):
        self.id = id
        self.url = f"{msconnector.MS_BASE_URL}/entity"
        self.headers = msconnector.ms_headers
        self.msconnector = msconnector

    def get_raw_data(self, expand:str=None) -> Dict:
        """ Получение сырых данных """
        payload = {"expand": expand}
        return session.get(url=self.url, headers=self.headers, params=payload).json()

    def positions(self, expand:str='positions.assortment') -> List:
        """ Дёргает позиции документа

        Args:
            expand (str, optional): погружение в поле. Defaults to 'assortment'.

        Returns:
            List: список позиций
        """
        payload = {'expand': expand}
        return [Position(self.msconnector,
                                entity_id=self.id,
                                raw_data=position,
                                url=self.url
                                ) for position in session.get(url=f"{self.url}/positions",
                           headers=self.headers,
                           params=payload).json()['rows']]

    @property
    def attributes_list(self) -> Dict:
        """ получить список доп. полей документа """
        return session.get(url=self.attrs_list_url, headers=self.headers).json()['rows']

    def get_attribute(self, attr_id:str) -> Dict:
        """ получить конкретное поле документа по id аттрибута """
        return session.get(url=f"{self.attrs_list_url}/{attr_id}", headers=self.headers).json()

    def delete(self):
        """ удалить данный документ """
        return session.delete(url=self.url, headers=self.headers)

    def put_data(self, raw_data:Dict):
        """ Запрос на изменение документа """
        return session.put(url=self.url, headers=self.headers, data=raw_data)

class MSOrder(Entity):

    def __init__(self, msconnector: MoySkladConnector, id:str):
        super().__init__(msconnector, id)
        self.attrs_list_url = f"{self.url}/customerorder/metadata/attributes"
        self.url = f"{self.url}/customerorder/{self.id}"

    def __str__(self) -> str:
        return f"{self.__class__.__name__} <id:{self.order_id}>"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__} <id:{self.order_id}>"

class MSMove(Entity):

    def __init__(self, msconnector: MoySkladConnector, id:str):
        super().__init__(msconnector, id)
        self.attrs_list_url =  f"{self.url}/move/metadata/attributes"
        self.url = f"{self.url}/move/{self.id}"

    def __str__(self) -> str:
        return f"{self._class__.__name__} <id:{self.id}>"

    def __repr__(self) -> str:
        return f"{self._class__.__name__} <id:{self.id}>"

class MSSupply(Entity):

    def __init__(self, msconnector: MoySkladConnector, id:str):
        super().__init__(msconnector, id)
        self.attrs_list_url =  f"{self.url}//metadata/attributes"
        self.url = f"{self.url}/supply/{self.id}"

    def __str__(self) -> str:
        return f"{self._class__.__name__} <id:{self.id}>"

    def __repr__(self) -> str:
        return f"{self._class__.__name__} <id:{self.id}>"

#! <---------- Entities by list ---------------------------------------------->

class EntitiesList:

    def __init__(self, msconnector: MoySkladConnector):
        self.url = f"{msconnector.MS_BASE_URL}/entity"

    def get(self, filters=None, expand=None):
        payload = {
            "filter":filters,
            "expand":expand
        }
        return session.get(
            url=self.url,
            headers=self.headers,
            params=payload
        ).json().get('rows')

class MSMovesList(EntitiesList):

    def __init__(self, msconnector: MoySkladConnector):
        super().__init__(msconnector)
        self.url = f"{self.url}/move"

class MSOrdersList(EntitiesList):

    def __init__(self, msconnector: MoySkladConnector):
        super().__init__(msconnector)
        self.url = f"{self.url}/customerorder"

class SuppliesList(EntitiesList):

    def __init__(self, msconnector: MoySkladConnector):
        super().__init__(msconnector)
        self.url = f"{self.url}/supply"

if __name__ == "__main__":
    msc = MoySkladConnector(ms_token)

