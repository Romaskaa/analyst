from .mocks import mock_metrika

all_metrics = [item["metrics"][0] for item in mock_metrika["data"]]

# Суммируем с помощью встроенной функции sum() - очень быстро на C уровне
total = sum(all_metrics)
average = round(total / len(all_metrics))
print(average)

links = []
for i in mock_metrika["data"]:
    if i["metrics"][0] < average:
        links.append(i["dimensions"][0]["id"])

print(links)

"""
[
    "/uslugi/hosting-1s",
    "/programmy/pricelist",
    "/gossektor/",
    "/uslugi/integraciya-1s-s-marketplejsami",
    "/blog/detail/crm-dlya-stomatologii",
    "/servisy/oblachnye-resheniya/arenda-1s",
    "/programmy/otrasli/",
    "/uslugi/po-dlya-biznesa",
    "/o-kompanii/",
    "/blog/detail/sdacha-polugodovoj-otchetnosti",
    "/akcii-i-meropriyatiya/",
    "/servisy/1s-elektronnyj-dokumentooborot",
    "/programmy/1s-gosudarstvennye-i-munitsipalnye-zakupki-8",
    "/uslugi/markirovka-1s",
    "/programmy/1s-bitrix",
    "/servisy/1s-kontragent",
    "/programmy/1s-bukhgalteriya-gosudarstvennogo-uchrezhdeniya",
    "/nashi-rezultaty/vnedrennye-resheniya/",
    "/uslugi/importozameshchenie",
    "/uslugi/realnaya-avtomatizaciya",
    "/servisy/oblachnye-resheniya/bitrix24",
    "/programmy/1s-zarplata-i-kadry-gosudarstvennogo-uchrezhdeniya",
    "/servisy/1spark-riski",
    "/kntakty",
    "/uslugi/udalennyy-sistemnyy-administrator",
    "/programmy/1s-demo",
    "/servisy/1s-otchetnost",
    "/gossektor/programmy",
    "/karera",
    "/o-kompanii/novosti/196446",
    "/o-kompanii/politika-konfidencialnosti",
    "/o-kompanii/obrabotka-personalnyh-dannyh",
    "/blagodarstvennye-pisma",
    "/akcii-i-meropriyatiya/akcii/182123",
    "/nashi-rezultaty/vnedrennye-resheniya/195412",
]
"""