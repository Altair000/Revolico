from threading import Thread
import pytz
import telebot
from datetime import datetime
from curl_cffi import requests as rq
from telebot import types
from flask import Flask, request

# Inicializar el bot con tu token de Telegram
TOKEN = '7812397450:AAH41sXqZYVvd0VyS5DRcisQ3UHwLVfJeBw'
bot = telebot.TeleBot(TOKEN, threaded=False)
# Inicializar Flask
app = Flask(__name__)
WEBHOOK_URL = ''

busqueda = None

# Función para calcular el tiempo transcurrido desde la publicación
def tiempo_transcurrido(fecha_publicacion):
    # Obtener la hora de La Habana
    cuba_tz = pytz.timezone('America/Havana')
    ahora = datetime.now(cuba_tz)  # Hora actual en La Habana
    fecha_pub = datetime.strptime(fecha_publicacion, "%Y-%m-%dT%H:%M:%S.%fZ")
    fecha_pub = cuba_tz.localize(fecha_pub)  # Asegurarse de que la fecha está en el horario de Cuba
    delta = ahora - fecha_pub
    if delta.days == 0:
        # Si es hoy, mostrar en horas o minutos
        if delta.seconds < 3600:
            minutos = delta.seconds // 60
            return f"hace {minutos} minuto(s)"
        else:
            horas = delta.seconds // 3600
            return f"hace {horas} hora(s)"
    else:
        # Si no es hoy, mostrar la fecha completa
        return fecha_pub.strftime("%d/%m/%Y %H:%M:%S")

# Función para obtener productos con paginación
def get_products(contains, page=1):
    try:
        home = rq.get('https://www.revolico.com/', impersonate='chrome')
        home.raise_for_status()

        search_data = [
            {
                'operationName': 'AdsSearch',
                'variables': {
                    'subcategorySlug': 'servicios_restaurantes-gastronomia',
                    'contains': contains,
                    'sort': [
                        {
                            'order': 'desc',
                            'field': 'updated_on_to_order_date',
                        },
                        {
                            'order': 'desc',
                            'field': 'relevance',
                        },
                    ],
                    'provinceSlug': 'la-habana',
                    'page': page,
                    'pageLength': 5,  # Mostrar solo 5 productos por página
                },
                'query': 'query AdsSearch($category: ID, $subcategory: ID, $contains: String, $price: BasePriceFilterInput, $sort: [adsPerPageSort], $hasImage: Boolean, $categorySlug: String, $subcategorySlug: String, $page: Int, $provinceSlug: String, $municipalitySlug: String, $pageLength: Int) {\n  adsPerPage(\n    category: $category\n    subcategory: $subcategory\n    contains: $contains\n    price: $price\n    hasImage: $hasImage\n    sort: $sort\n    categorySlug: $categorySlug\n    subcategorySlug: $subcategorySlug\n    page: $page\n    provinceSlug: $provinceSlug\n    municipalitySlug: $municipalitySlug\n    pageLength: $pageLength\n  ) {\n    pageInfo {\n      startCursor\n      endCursor\n      hasNextPage\n      hasPreviousPage\n      pageCount\n      __typename\n    }\n    edges {\n      node {\n        id\n        title\n        price\n        currency\n        permalink\n        imagesCount\n        updatedOnToOrder\n        isPromoted\n        provinceId\n        municipalityId\n        mainImage {\n          gcsKey\n          __typename\n        }\n        viewCount\n        __typename\n      }\n      __typename\n    }\n    meta {\n      total\n      __typename\n    }\n    __typename\n  }\n}',
            },
        ]

        search = rq.post('https://graphql-api.revolico.app/', json=search_data, impersonate='chrome')
        search.raise_for_status()
        search_json = search.json()

        # Listas para almacenar los datos
        ids = []
        titulos = []
        precios = []
        monedas = []

        # Extraer los datos de la respuesta
        for ad in search_json[0]['data']['adsPerPage']['edges']:
            node = ad['node']
            ids.append(node['id'])
            titulos.append(node['title'])
            precios.append(node['price'])
            monedas.append(node['currency'])

        # Información de la paginación
        page_info = search_json[0]['data']['adsPerPage']['pageInfo']
        has_previous_page = page_info['hasPreviousPage']
        has_next_page = page_info['hasNextPage']

        # Generar los botones inline
        buttons = []
        for index, title in enumerate(titulos):
            buttons.append(types.InlineKeyboardButton(
                f"{index + 1} - {title} - {precios[index]} {monedas[index]}",
                callback_data=f"product_{ids[index]}"
            ))

        # Crear un teclado con los botones
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(*buttons)

        # Agregar botones de paginación
        pagination_buttons = []

        # Botón "Anterior"
        if has_previous_page:
            pagination_buttons.append(types.InlineKeyboardButton("⬅️ Anterior", callback_data=f"page_{page - 1}"))

        # Botón "Siguiente"
        if has_next_page:
            pagination_buttons.append(types.InlineKeyboardButton("Siguiente ➡️", callback_data=f"page_{page + 1}"))

        if pagination_buttons:
            keyboard.add(*pagination_buttons)

        return keyboard, ids

    except Exception as e:
        return None, str(e)

def details(selected_id):
    try:
        details_data = [
            {
                'operationName': 'AdDetails',
                'variables': {
                    'id': selected_id,
                },
                'query': 'query AdDetails($id: ID!, $token: String) {\n  ad(id: $id, token: $token) {\n    ...AdD2020\n    email(mask: true)\n    subcategory {\n      id\n      title\n      slug\n      parentCategory {\n        id\n        title\n        slug\n        __typename\n      }\n      __typename\n    }\n    viewCount\n    permalink\n    firstPhonePrefix\n    firstPhoneType\n    firstPhone\n    secondPhonePrefix\n    secondPhoneType\n    secondPhone\n    whatsapp\n    mainImage {\n      gcsKey\n      __typename\n    }\n    __typename\n  }\n}\n\nfragment AdD2020 on AdType {\n  id\n  title\n  shortDescription\n  description\n  price\n  currency\n  name\n  status\n  imagesCount\n  readyImages {\n    id\n    createdKey\n    gcsKey\n    __typename\n  }\n  contactInfo\n  updatedOnByUser\n  isPromoted\n  province {\n    id\n    slug\n    name\n    __typename\n  }\n  municipality {\n    id\n    slug\n    name\n    __typename\n  }\n  __typename\n}',
            },
        ]

        details = rq.post('https://graphql-api.revolico.app/', json=details_data, impersonate='chrome')
        details.raise_for_status()
        details_json = details.json()

        # Extraer los valores del anuncio
        ad = details_json[0]['data']['ad']

        # Información extraída
        titulo = ad['title']
        descripcion = ad['description']
        precio = ad['price']
        moneda = ad['currency']
        nombre = ad['name']
        fecha_publicacion = ad['updatedOnByUser']
        vistas = ad['viewCount']
        telefono = ad['firstPhone']
        provincia = ad['province']['name']
        municipio = ad['municipality']['name']

        # Formatear la salida
        fecha_formateada = tiempo_transcurrido(fecha_publicacion)

        # Crear el mensaje final
        mensaje = f"""
        Producto: {titulo}
        Descripción: {descripcion}
        Publicado: {fecha_formateada}
        Vistas: {vistas}
        Precio: {precio}
        Moneda: {moneda}
        Contacto: {nombre}
        Teléfono: {telefono}
        Provincia: {provincia}
        Municipio: {municipio}
        """

        # Enviar mensaje con la información y el botón
        return mensaje

    except Exception as e:
        return f"Error: {e}."

# Función para manejar el comando /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id, "Hola Pulse aquí -> [/search] para comenzar a buscar.")

# Función para manejar el comando /search
@bot.message_handler(commands=['search'])
def handle_search(message):
    bot.send_message(message.chat.id, "Por favor, ingresa el nombre o descripción del producto a buscar:")
    bot.register_next_step_handler(message, search_for_product)

# Función para manejar la búsqueda del producto
def search_for_product(message):
    global busqueda
    query = message.text
    busqueda = query
    bot.send_message(message.chat.id, "Buscando productos...")
    keyboard, ids = get_products(query)

    if keyboard:
        bot.send_message(message.chat.id, "Selecciona un producto:", reply_markup=keyboard)
    else:
        bot.send_message(message.chat.id, "No se encontraron productos o hubo un error.")

# Función para manejar la selección de un producto
@bot.callback_query_handler(func=lambda call: call.data.startswith('product_'))
def handle_product_selection(call):
    product_id = call.data.split('_')[1]
    bot.answer_callback_query(call.id, "Cargando detalles del producto...")
    mensaje = details(product_id)
    # Aquí puedes agregar el código para obtener detalles del producto con su ID
    bot.send_message(call.message.chat.id, mensaje)

@bot.callback_query_handler(func=lambda call: call.data.startswith('page_'))
def handle_pagination(call):
    try:
        # Obtener el número de página desde el callback_data
        page = int(call.data.split('_')[1])

        # Obtener los productos de la nueva página
        keyboard, ids = get_products(busqueda, page)
        bot.edit_message_text("Productos encontrados:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=keyboard)

    except Exception as e:
        bot.send_message(call.message.chat.id, f"Error al cargar los productos: {e}")

@app.route("/")
def home():
    return "Bot funcionando"

# Ruta de Flask para el webhook
@app.route(f"/{TOKEN}", methods=["POST"])
def receive_update():
    json_update = request.stream.read().decode("utf-8")
    update = telebot.types.Update.de_json(json_update)
    bot.process_new_updates([update])
    return "OK", 200

# Establece la webhook al iniciar
@app.route("/set_webhook", methods=["GET", "POST"])
def set_webhook():
    success = bot.set_webhook(url=WEBHOOK_URL + f"/{TOKEN}")
    if success:
        return "Webhook configurada correctamente", 200
    else:
        return "Fallo al configurar el webhook", 500

# Elimina la webhook si es necesario
@app.route("/delete_webhook", methods=["GET", "POST"])
def delete_webhook():
    bot.delete_webhook()
    return "Webhook eliminada correctamente", 200

# Ejecuta el bot en un hilo separado
def run_bot():
    bot.polling()

if __name__ == "__main__":
    Thread(target=run_bot).start()
    app.run(host="0.0.0.0", port=0)