"""
Пакет для работы с API МойСклад
MS doc: https://dev.moysklad.ru/doc/api/remap/1.2/documents/
Пока что в данном пакете реализованы классы для
работы со следующими сущностями:
  - Заказ;
  - перемещение;
  - оприходование
  - списания;
  - товаров;
  - отгрузок;
  - счетов поставщиков
Работа с ними разделяется на оперирование с единчными
сущностми и на оперирование со списком сущностей.
Методы работы с единичными сущностями:
  - Получение позиций сущности;
  - получение доп. аттрибуты;
  - получение сырые данные;
  - удаление сущности;
  - внесение в сущность изменений

TODO: Реализовать создание документов
"""
import os
from typing import Dict, List, Union, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
import ujson

session = requests.Session()
retry = Retry(connect=4, backoff_factor=1)
adapter = HTTPAdapter(max_retries=retry)
session.mount('http://', adapter)
session.mount('https://', adapter)


class MoySkladConnector:
    """ Коннекто МС для формирования хедеров """
    ms_base_url = 'https://online.moysklad.ru/api/remap/1.2'

    def __init__(self, token: str):
        self.token = token
        self.ms_headers = {
            "Authorization": self.token,
            "Content-Type": "application/json",
            "Connection": "keep-alive"
        }


class Stocks:
    """ Класс для получения остатков с МС """
    def __init__(self, msconnector: MoySkladConnector):
        self.MS_STOCKS_BASE_URL = f"{msconnector.ms_base_url}/report/stock"
        self.headers = msconnector.ms_headers

    def get_stocks(self,
                   limit: int = None,
                   offset: int = None,
                   filters: str = None,
                   expand: str = None,
                   group_by: str = 'variant'
                   ) -> dict:
        """ Получить остатки
        https://dev.moysklad.ru/doc/api/remap/1.2/reports/#otchety-otchet-ostatki-poluchit-ostatki

        Args:
            limit (int, optional): Максимальное количество сущностей для
            извлечения. Defaults to None.
            offset (int, optional): Отступ в выдаваемом списке сущностей.
            Defaults to None.
            filters (str, optional): фильтры. Defaults to None.
            groupBy (str, optional): тип, по которому нужно сгруппировать
            выдачу (`variant`,`product`,`consignment`). Defaults to 'variant'.

        Returns:
            dict: _description_
        """
        url = f'{self.MS_STOCKS_BASE_URL}/all'
        payload = {
            "limit": limit,
            "offset": offset,
            "groupBy": group_by,
            "filter": filters,
            "expand": expand
        }
        return session.get(url=url, headers=self.headers, params=payload).json()

    def get_stocks_bystore(self,
                           limit: int = None,
                           offset: int = None,
                           filters: str = None,
                           expand: str = None,
                           group_by: str = 'variant'
                           ) -> dict:
        """ Остатки по складам
        https://dev.moysklad.ru/doc/api/remap/1.2/reports/#otchety-otchet-ostatki-poluchit-ostatki-po-skladam

        Args:
            limit (int, optional): Максимальное количество сущностей для
            извлечения. Defaults to None.
            offset (int, optional): Отступ в выдаваемом списке сущностей.
            Defaults to None.
            filters (str, optional): фильтры. Defaults to None.
            group_by (str, optional): тип, по которому нужно сгруппировать
            выдачу ('product', 'variant', 'consignment'). Defaults to 'variant'.

        Returns:
            dict: _description_
        """
        url = f'{self.MS_STOCKS_BASE_URL}/bystore'
        payload = {
            "limit": limit,
            "offset": offset,
            "groupBy": group_by,
            "filter": filters,
            "expand": expand
        }
        return session.get(url=url, headers=self.headers, params=payload).json()

    def get_current_stocks(self,
                           mode: str = 'all',
                           stockType: str = 'stock',
                           filters: str = None,
                           expand: str = None
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
            "stockType": stockType,
            "filter": filters,
            "expand": expand
        }
        return session.get(url=url, headers=self.headers, params=payload).json()


class Position:
    """ Позиции товаров в документе """

    def __init__(self,
                 msconnector: MoySkladConnector,
                 url: str,
                 pos_id: Optional[str] = None,
                 raw_data: Optional[dict] = None
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
        """ Словарь с сырыми данными """
        payload = {"expand": "assortment"}
        return session.get(url=self.entity_position_url,
                           headers=self.headers,
                           params=payload).json()

    @property
    def assortment(self):
        """ Данные по товару """
        return self.raw_data['assortment']

#! <---------- Single entity ------------------------------------------------->


class Entity:
    """ Абстрактный класс сущностей (Перемещение, заказ и т.д.)

    Args:
        msconnector (MoySkladConnector): коннкетор МС
        id (str, optional): id сущности. Defaults to None.
        raw (Dict, optional): сырые данные|словарь с данными сущности. Defaults to None.
    """

    def __init__(self,
                 msconnector: MoySkladConnector,
                 entity_id: Optional[str]=None,
                 raw: Optional[Dict] = None):
        if entity_id or raw:
            self.id = entity_id or raw.get('id')
        self.url = f"{msconnector.ms_base_url}/entity"
        self.headers = msconnector.ms_headers
        self.msconnector = msconnector

    @property
    def meta(self):
        """ Достатёт мету текущего документа """
        return {'meta': self.raw.get('meta')}


    def raw(self, expand: str = None) -> Dict:
        """ Получение сырых данных """
        payload = {"expand": expand}
        return session.get(url=self.url,
                           headers=self.headers,
                           params=payload).json()

    def positions(self, expand: str = 'positions.assortment') -> List:
        """ Дёргает позиции документа

        Args:
            expand (str, optional): погружение в поле. Defaults to 'assortment'.

        Returns:
            List: список позиций
        """
        payload = {'expand': expand}
        return [Position(self.msconnector,
                         pos_id=self.id,
                         raw_data=position,
                         url=self.url
                         ) for position in session.get(url=f"{self.url}/positions",
                                                       headers=self.headers,
                                                       params=payload).json().get('rows')]

    @property
    def attributes_list(self) -> Dict:
        """ получить список доп. полей документа """
        return session.get(url=self.attrs_list_url, headers=self.headers).json().get('rows')

    def get_attribute(self, attr_id: str) -> Dict:
        """ получить конкретное поле документа по id аттрибута """
        return session.get(url=f"{self.attrs_list_url}/{attr_id}", headers=self.headers).json()

    def delete(self):
        """ удалить данный документ """
        return session.delete(url=self.url, headers=self.headers)

    def put_data(self, raw_data: Dict):
        """ Запрос на изменение документа """
        return session.put(url=self.url, headers=self.headers, data=raw_data)


class Product(Entity):
    """ Сущность товара

    Args:
        msconnector (MoySkladConnector): коннектор МС
        id (str, optional): id конкретного товара. Defaults to None.
        raw (Dict, optional): сырые данные|словарь с товаром. Defaults to None.
    """

    def __init__(self, msconnector: MoySkladConnector, entity_id:str=None, raw:Dict=None):
        super().__init__(msconnector, entity_id, raw)
        self.url = f"{self.url}/product/{self.id}"
        self.attrs_list_url = f"{self.url}/product/metadata/attributes"

    @property
    def barcodes(self):
        """ Возвращает баркоды товара """
        #TODO: в душе не понимаю как работает, я не интерпретатор, позже проверю
        return [','.join(list(barcode.values())) for barcode in self.raw().get('barcodes', [])]

    @property
    def article(self):
        """ Артикул товара """
        return self.raw().get('article')

    def __str__(self) -> str:
        return f"{self.__class__.__name__} <id:{self.id}>"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__} <id:{self.id}>"


class CustomerOrder(Entity):
    """ Документ заказа покупателя

    Args:
        msconnector (MoySkladConnector): коннектор МС
        id (str, optional): id конкретного заказа. Defaults to None.
        raw (Dict, optional): сырые данные|словарь заказа. Defaults to None.
    """

    def __init__(self, msconnector: MoySkladConnector, entity_id:str=None, raw:Dict=None):
        super().__init__(msconnector, entity_id, raw)
        self.url = f"{self.url}/customerorder"
        if id or raw:
            self.raw = raw or self.raw()
            self.url = f"{self.url}/{self.id}"
        self.attrs_list_url = f"{self.url}/metadata/attributes"

    def __str__(self) -> str:
        return f"{self.__class__.__name__} <id:{self.id}>"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__} <id:{self.id}>"

    def create(self, name:Union[str, int], organization:Dict, agent:Dict):
        """ Создать заказ

        Args:
            name (Union[str, int]): название/номер
            organization (Dict): мета организации
            agent (Dict): мета контрагента

        Returns:
            Response: ответ на создание заказа
        """
        payload = ujson.dumps({
            "name": name,
            "organization": organization,
            "agent": agent
        })
        return session.post(url=self.url, headers=self.headers, data=payload)

    def demands(self, expand:str=None) -> List[Dict]:
        """_summary_

        Args:
            expand (str, optional): прогрузить поле. Defaults to None.

        Returns:
            List[Dict]: список отгрузок заказа
        """
        payload = {
            "expand":expand
        }
        return [
            session.get(
                url=demand.get('meta', {}).get('href'),
                headers=self.headers,
                params=payload
            ).json() for demand in self.raw.get('demands', {})]


class Move(Entity):
    """ Документ перемещения

    Args:
        msconnector (MoySkladConnector): коннектор МС
        id (str, optional): id конкретного перемещения. Defaults to None.
        raw (Dict, optional): сырые данные|словарь с перемещением. Defaults to None.
    """

    def __init__(self, msconnector: MoySkladConnector, entity_id:str=None, raw:Dict=None):
        super().__init__(msconnector, entity_id, raw)
        self.attrs_list_url = f"{self.url}/move/metadata/attributes"
        self.url = f"{self.url}/move/{self.id}"

    def __str__(self) -> str:
        return f"{self.__class__.__name__} <id:{self.id}>"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__} <id:{self.id}>"


class Supply(Entity):
    """ Документ приемки

    Args:
        msconnector (MoySkladConnector): коннектор МС
        id (str, optional): id конкретной приемки. Defaults to None.
        raw (Dict, optional): сырые данные|словарь с приемкой. Defaults to None.
    """

    def __init__(self, msconnector: MoySkladConnector, entity_id:str=None, raw:Dict=None):
        super().__init__(msconnector, entity_id, raw)
        self.attrs_list_url = f"{self.url}/supply/metadata/attributes"
        self.url = f"{self.url}/supply/{self.id}"

    def __str__(self) -> str:
        return f"{self.__class__.__name__} <id:{self.id}>"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__} <id:{self.id}>"


class Loss(Entity):
    """ Документ списания

    Args:
        msconnector (MoySkladConnector): коннектор МС
        id (str, optional): id конкретного списания. Defaults to None.
        raw (Dict, optional): сырые данные|словарь со списанием. Defaults to None.
    """

    def __init__(self, msconnector: MoySkladConnector, entity_id:str=None, raw:Dict=None):
        super().__init__(msconnector, entity_id, raw)
        self.attrs_list_url = f"{self.url}/loss/metadata/attributes"
        self.url = f"{self.url}/supply/{self.id}"

    def __str__(self) -> str:
        return f"{self.__class__.__name__} <id:{self.id}>"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__} <id:{self.id}>"


class InvoiceIn(Entity):
    """ Документ - счет поставщика

    Args:
        msconnector (MoySkladConnector): коннектор МС
        id (str, optional): id конкретного счета. Defaults to None.
        raw (Dict, optional): сырые данные|словарь со счетом. Defaults to None.
    """

    def __init__(self, msconnector: MoySkladConnector, entity_id:str=None, raw:Dict=None):
        super().__init__(msconnector, entity_id, raw)
        self.attrs_list_url = f"{self.url}/invoicein/metadata/attributes"
        self.url = f"{self.url}/invoicein/{self.id}"

    def __str__(self) -> str:
        return f"{self.__class__.__name__} <id:{self.id}>"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__} <id:{self.id}>"


class Demand(Entity):
    """ Документ отгрузки

    Args:
        msconnector (MoySkladConnector): коннектор МС
        id (str, optional): id конкретной отгрузки. Defaults to None.
        raw (Dict, optional): сырые данные|словарь с отгрузкой. Defaults to None.
    """

    def __init__(self, msconnector: MoySkladConnector, entity_id:str=None, raw:Dict=None):
        super().__init__(msconnector, entity_id, raw)
        self.attrs_list_url = f"{self.url}/demand/metadata/attributes"
        self.url = f"{self.url}/demand/{self.id}"

    def __str__(self) -> str:
        return f"{self.__class__.__name__} <id:{self.id}>"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__} <id:{self.id}>"


class Organization(Entity):
    """ Сущность организации

    Args:
        msconnector (MoySkladConnector): коннектор МС
        id (str): id конкретной организации
    """

    def __init__(self, msconnector: MoySkladConnector, entity_id:str=None):
        super().__init__(msconnector, entity_id)
        self.attrs_list_url = f"{self.url}/organization/metadata/attributes"
        self.url = f"{self.url}/organization/{self.id}"

    def __str__(self) -> str:
        return f"{self.__class__.__name__} <id:{self.id}>"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__} <id:{self.id}>"


class Counterparty(Entity):
    """ Сущность контрагента

    Args:
        msconnector (MoySkladConnector): коннектор МС
        id (str): id конкретного контрагента
    """

    def __init__(self, msconnector: MoySkladConnector, entity_id:str):
        super().__init__(msconnector, entity_id)
        self.attrs_list_url = f"{self.url}/counterparty/metadata/attributes"
        self.url = f"{self.url}/counterparty/{self.id}"

    def __str__(self) -> str:
        return f"{self.__class__.__name__} <id:{self.id}>"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__} <id:{self.id}>"

#! <---------- Entities by list ---------------------------------------------->


class EntitiesList:
    """ Абстрактный класс для сущностей и документов

    args:
        msconnector (MoySkladConnector): коннектор МС
    """

    def __init__(self, msconnector: MoySkladConnector):
        self.url = f"{msconnector.ms_base_url}/entity"
        self.headers = msconnector.ms_headers
        self.msconnector = msconnector

    def get(self, filters:str=None, expand:str=None, next_href:str=None) -> List[Dict]:
        """ Возвращает список документов

        Args:
            filters (str, optional): фильтры. Defaults to None.
            next_href (str, optional): следующая ссылка для рекурсии. Defaults to None.
            expand (str, optional): погружение в поле. Defaults to None.

        Returns:
            dict: товары, соответствующие запросу
        """
        payload = {
            "filter": filters,
            "expand": expand
        }
        response = session.get(
            url=next_href or self.url, headers=self.headers, params=payload).json()
        result = response.get('rows')
        if response['meta'].get('nextHref'):
            result.extend(self.get(next_href=response['meta']['nextHref']))
        return result


class Assortment(EntitiesList):
    """ Список товаров (Почти то же, что и Products
    только с остатками и возможностью отифильтровать
    по складу) """

    def __init__(self, msconnector: MoySkladConnector):
        super().__init__(msconnector)
        self.url = f"{self.url}/assortment"
        self.headers = msconnector.ms_headers


class MovesList(EntitiesList):
    """ список перемещений """

    def __init__(self, msconnector: MoySkladConnector):
        super().__init__(msconnector)
        self.url = f"{self.url}/move"


class CustomerOrdersList(EntitiesList):
    """ Список заказов покупателей """

    def __init__(self, msconnector: MoySkladConnector):
        super().__init__(msconnector)
        self.url = f"{self.url}/customerorder"


class SuppliesList(EntitiesList):
    """ список оприходований """

    def __init__(self, msconnector: MoySkladConnector):
        super().__init__(msconnector)
        self.url = f"{self.url}/supply"


class LossList(EntitiesList):
    """ список списаний """

    def __init__(self, msconnector: MoySkladConnector):
        super().__init__(msconnector)
        self.url = f"{self.url}/loss"


class InvoiceInList(EntitiesList):
    """ список счетов поставщиков """

    def __init__(self, msconnector: MoySkladConnector):
        super().__init__(msconnector)
        self.url = f"{self.url}/invoicein"


class DemandsList(EntitiesList):
    """ список отгрузок """

    def __init__(self, msconnector: MoySkladConnector):
        super().__init__(msconnector)
        self.url = f"{self.url}/demand"


class ProductsList(EntitiesList):
    """ Список товаров """

    def __init__(self, msconnector: MoySkladConnector):
        super().__init__(msconnector)
        self.url = f"{self.url}/product"


class OrganizationsList(EntitiesList):
    """ список организаций """

    def __init__(self, msconnector: MoySkladConnector):
        super().__init__(msconnector)
        self.url = f"{self.url}/organization"


class CounterpartiesList(EntitiesList):
    """ Список контрагентов """

    def __init__(self, msconnector: MoySkladConnector):
        super().__init__(msconnector)
        self.url = f"{self.url}/counterparty"

if __name__ == "__main__":
    msc = MoySkladConnector(MS_TOKEN)