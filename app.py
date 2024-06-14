import const as const
import streamlit as st
import time
import json
 
from langchain.chat_models import ChatOpenAI
from langchain.schema import SystemMessage
from langchain.prompts import ChatPromptTemplate, HumanMessagePromptTemplate, MessagesPlaceholder, PromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain.chains import LLMChain
from langchain.llms import OpenAI
from langchain.callbacks import get_openai_callback

import openai

st.set_page_config(page_title="Evaluador de Riesgo Tecnológico")

st.markdown("""
    <style>
        [data-testid="stHeader"] {
            display: none !important;
        }
    </style>
""", unsafe_allow_html=True) 


def modeloMemoryLangChainOpenAI(api_key, modelo, contextoSystem):
    prompt = ChatPromptTemplate.from_messages([
        MessagesPlaceholder(variable_name="chat_history"), # Donde se guardará la memoria.
        HumanMessagePromptTemplate.from_template("La respuesta a la pregunta es <<{human_input}>>"), 
        SystemMessage(content=contextoSystem), # Mensaje persistente del sistema
    ])
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    
    llm = ChatOpenAI(temperature=0.7, openai_api_key = api_key, model=modelo)
    chat_llm_chain = LLMChain(
        llm=llm,
        prompt=prompt,
        verbose=False,
        memory=memory,
    )
    return chat_llm_chain


def generar_resumen(api_key, texto):
	prompt = ChatPromptTemplate.from_messages([
        	HumanMessagePromptTemplate.from_template("<<{human_input}>>"), 
        	SystemMessage(content="Resume el siguiente texto de manera muy formal y elimina las redundancias. El estilo de escritura debe ser como si fuera para un informe de auditoría:"), # Mensaje persistente del 
		])
    
	llm = ChatOpenAI(temperature=0.5, openai_api_key = api_key, model=ss["modeloGPT"])
	chat_llm_chain = LLMChain(
        	llm=llm,
        	prompt=prompt,
        	verbose=False,
    	)
	respuesta=chat_llm_chain.predict(human_input=texto)
	return respuesta

def contextoModelo(nombreIso,nombreClausula,nombreCategoria,nombreControl,descripcionControl,descripcionOrientacion,otraInformacion,pregunta1,otrosControles):
	return f"""
 Tu rol será de Auditor Informático y deberás realizar una evaluación de riesgos de seguridad de la información en relación a la descripción obtenida de la ISO {nombreIso}, del dominio {nombreClausula}, enfocándote únicamente en el siguiente control {nombreControl}:
 <<{descripcionControl}>>

 Con la siguiente información deberás orientarte para realizar las preguntas de auditoría:
 <<{descripcionOrientacion}
 Otra información: {otraInformacion}
 >>
 
 Con toda la información anterior, deberás realizar preguntas para verificar si se cumple con el control.

 No deberás realizar ninguna pregunta referente a otros controles como:
 {otrosControles}

 La salida de tu respuesta deberá ser siempre con el siguiente formato, y ningún otro formato:
 {{"respuesta":{{"Dudas":"<<Si quedas con dudas en las respuesta del usuario o aún te quedan preguntas por hacer, responde 'S', si quedas conforme y ya abarcaste todas las preguntas, responde 'N'>>","Pregunta":"<<Solo si en el item dudas la respuesta es 'S', deberás incorporar tu nueva consulta acá, si no entonces responde ''>>","Nota":"<<Solo si en el item dudas la respuesta es 'N', deberás evaluar el nivel de seguridad de 1 a 10, siendo el 1 el peor nivel y 10 el óptimo>>","Resumen":"<<Solo si en el item dudas la respuesta es 'N', deberás realizar un breve resumen de la respuesta solo con lo más importante>>","Hallazgo":"<<Solo si en el item dudas la respuesta es 'N' y si en el item 'nota' es menor o igual a 7, deberás redactar solo si existen los hallazgos de auditoría, sino entonces responde ''>>","Sugerencia":"<<Solo si en el item 'dudas' la respuesta es 'N' y si en el item 'nota' es menor o igual a 7, agrega tu sugerencia de auditoría a la observación, sino entonces responde ''>>"}}}}"""


def activaPreguntas (preguntasIsos):
	# Recorrer los dominios y preguntas y analiza cual toca preguntar
	for iso, info in preguntasIsos.items():
		if ss["iso_seleccionada"] == iso :
			for dominio in info["Clausula"]:
				if dominio['Nombre'] not in ss["options_clausulas"]:
					dominio['Aplica'] = "false"
					for categoria in dominio["Categorias"]:
						categoria['Aplica'] = "false"
	return preguntasIsos

def buscarPregunta (preguntasIsos):
	nombreIso = ""
	nombreClausula = ""
	nombreCategoria = ""
	objetivoCategoria = ""
	nombreControl = ""
	descripcionControl = ""
	descripcionOrientacion = ""
	otraInformacion = ""
	pregunta1 = ""
	preguntas = ""
	
	# Recorrer los dominios y preguntas y analiza cual toca preguntar
	for iso, info in preguntasIsos.items():
		if ss["iso_seleccionada"] == iso :
			nombreIso = info["NombreIso"]
			for clausula in info["Clausula"]:
				if clausula['Aplica'] == "true":
					for categoria in clausula["Categorias"]:
						if categoria['Aplica'] == "true":
							i=0
							for control in categoria["Control"]:
								if control["Impresa"] == "false":
									nombreClausula = clausula["Nombre"]
									nombreCategoria = categoria["Nombre"]
									objetivoCategoria = categoria["Objetivo"]
									nombreControl = control["Nombre"]
									descripcionControl = control["Control"]
									descripcionOrientacion = control["Orientacion"]
									otraInformacion = control["OtraInformacion"]
									pregunta1 = control["Pregunta1"]
									#preguntas = control["Preguntas"]
									break
									
	return nombreIso,nombreClausula,nombreCategoria,objetivoCategoria,nombreControl,descripcionControl,descripcionOrientacion,otraInformacion,pregunta1


def buscaOtrosControles(preguntasIsos,nombreClausula,nombreCategoria,nombreControl):
	otrosControles = ""
	for iso, info in preguntasIsos.items():
		if ss["iso_seleccionada"] == iso :
			for clausula in info["Clausula"]:
				if clausula['Nombre'] == nombreClausula:
					for categoria in clausula["Categorias"]:
						if categoria['Nombre'] == nombreCategoria:
							for control in categoria["Control"]:
								if control["Nombre"] != nombreControl:
									otrosControles += " - "+control["Nombre"]+"\n"
	
	return otrosControles


def cleanVariablesSesion():
	ss["nombreIso"] = ""
	ss["nombreClausula"] = ""
	ss["nombreCategoria"] = ""
	ss["nombreControl"] = ""
	ss["descripcionControl"] = ""
	ss["descripcionOrientacion"] = ""
	ss["otraInformacion"] = ""
	ss["pregunta1"] = ""
	#ss["preguntas"] = ""
	del st.session_state["chat_llm_chain"]
	del st.session_state["messages"]

def custom_serializer(obj):
    """Función personalizada para serializar objetos no soportados por defecto."""
    if isinstance(obj, const):
        # Retorna una representación serializable del objeto
        return obj.mi_metodo_de_serializacion()
    # Para otros tipos, puedes añadir más condiciones aquí
    
    # Si el objeto no es de un tipo manejado, lanza TypeError
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


def getControlRespuestas():
	controlRespuestas = ""
	for iso, info in preguntasIsos.items():
		if ss["iso_seleccionada"] == iso :
			for clausula in info["Clausula"]:
				if clausula["Aplica"] == "true":
					for categoria in clausula["Categorias"]:
						if categoria['Aplica'] == "true":
							for control in categoria["Control"]:
								if control["Impresa"] == "true":
									controlRespuestas += "Descripción Control: <<"+control["Control"]+">> - Resumen Respuestas: <<"+control['resumen']+">>\n"
									
	return controlRespuestas


#####################################
# __main__


#Inicializar general
ss = st.session_state
if "modeloGPT" not in ss:
	ss["modeloGPT"] = "gpt-4-0125-preview" #"gpt-4" "gpt-4o-2024-05-13"
if "proceso" not in ss:
	ss["proceso"] = "NivelEvaluacion"
if "options_dominios" not in ss:
	ss["options_dominios"] = []
if "nombreDominio" not in ss:
	ss["nombreDominio"] = ""
if "descripcionDominio" not in ss:
	ss["descripcionDominio"] = ""
if "pregunta1" not in ss:
	ss["pregunta1"] = ""
if "preguntasIsos" not in ss or ss["proceso"] == "NivelEvaluacion":
	#preguntasIsos = const
	json_str = json.dumps(const.isos, default=custom_serializer)
	preguntasIsos = json.loads(json_str)
	
	ss["preguntasIsos"] = []
else:		
	preguntasIsos = ss["preguntasIsos"]
openai_api_key = st.secrets["api_key"]



#######################
### Menu Lateral ###

params = st.experimental_get_query_params()
mostrarBarra = False
if "lkn" in params:
	if params["lkn"][0] == "view":
		mostrarBarra = False

if mostrarBarra:	
	with st.sidebar:

	    #openai_api_key = st.text_input("OpenAI API Key", key="chatbot_api_key", type="password")
	    st.sidebar.header('Autoevaluador de Riesgos Tecnológicos')
	    st.markdown("""
	        <div style="text-align: justify;">
	            Bienvenido al asistente IA de evaluación de riesgos tecnológicos. Este chatbot está diseñado para guiarlo en una encuesta de autoevaluación, la cual permitirá conocer deficiencias en su organización relacionadas a la seguridad de la información. Finalmente, el sistema procesará la información y entregará el resultado del análisis realizado. Lo único que se solicita al usuario, es que conteste las preguntas con honestidad.
	        </div>
	    """, unsafe_allow_html=True)
	    st.text("")
	    st.sidebar.header('Aplicación creada por \n')
	    "[Víctor Vásquez](https://www.linkedin.com/in/victorvasquezrivas/)"
	    "[victorvasquezrivas@gmail.com](mailto:victorvasquezrivas@gmail.com)"
	    st.text("")
	    st.markdown("""
		<div style="text-align: justify;">
	            Si te fue útil o te pareció interesante, coméntamelo a mi correo. 
	        </div>
		""", unsafe_allow_html=True)

### Fin Menu Lateral ###
#######################




#######################
### NivelEvaluacion ###
if ss["proceso"] == "NivelEvaluacion":
	st.title("Evaluación de Riesgos Tecnológicos")
	st.write(" ")
	st.write(" ")
	st.write(" ")

	# Lista las ISO en el selectbox
	nombres_isos = list(const.isos.keys())
	st.subheader(f"Tipo de evaluación: {nombres_isos[0]}")
	iso_seleccionada=nombres_isos[0]
	#iso_seleccionada = st.selectbox("Seleccione el tipo de evaluación", nombres_isos)

	st.write(" ")
	st.write(" ")
	
	# Acceder a los clausulas de la ISO especificada
	clausulas = const.isos[iso_seleccionada]["Clausula"]
	# Extraer los nombres de los clausulas
	nombres_clausulas = [clausula["Nombre"] for clausula in clausulas]
	options_clausulas = st.multiselect('Seleccione la o las cláusulas:',nombres_clausulas,placeholder="Agregue todos los clausula que evaluará")

	st.write(" ")
	st.write(" ")
	
	# Selección del nivel de evaluación
	#nivel_evaluacion = st.slider("Seleccione el nivel de profundidad en la evaluación:", min_value=1, max_value=10, value=10)
	#st.info(f"La cantidad de tiempo aproximado en la evaluación será de : {str(round(150*(nivel_evaluacion/10)*len(options_clausulas)/11))} minutos")

	st.write(" ")
	st.write(" ")
	
	# Btn Aceptar nivel evaluación
	if st.button('Evaluar'):
		if len(options_clausulas) == 0:
			st.warning('Debe seleccionar al menos 1 clausula', icon="⚠️")
		else:
			ss["proceso"] = "Chat"
			#ss["nivel_evaluacion"] = nivel_evaluacion
			ss["iso_seleccionada"] = iso_seleccionada
			ss["options_clausulas"] = options_clausulas
			ss["preguntasIsos"] = activaPreguntas (preguntasIsos)
			st.rerun()
			
### FIN NivelEvaluacion ###
###########################



###########################
### Chat ###
if ss["proceso"] == "Chat":
	
	if "total_tokens" not in ss:
		ss["total_tokens"] = 0
	
	# Buscar pregunta
	if ss["pregunta1"] == "":
		ss["nombreClausula"]=""
		ss["nombreCategoria"]=""
		ss["objetivoCategoria"]=""
		ss["nombreIso"],ss["nombreClausula"],ss["nombreCategoria"],ss["objetivoCategoria"], ss["nombreControl"],ss["descripcionControl"],ss["descripcionOrientacion"],ss["otraInformacion"],ss["pregunta1"] = buscarPregunta(preguntasIsos)
		otrosControles = buscaOtrosControles(preguntasIsos,ss["nombreClausula"],ss["nombreCategoria"],ss["nombreControl"])
		ss["chat_llm_chain"] = modeloMemoryLangChainOpenAI(openai_api_key, ss["modeloGPT"], contextoModelo(ss["nombreIso"],ss["nombreClausula"],ss["nombreCategoria"],ss["nombreControl"],ss["descripcionControl"],ss["descripcionOrientacion"],ss["otraInformacion"],ss["pregunta1"],otrosControles))
	
	
	# Ya no quedan más preguntas
	if ss["pregunta1"] == "": 
		ss["proceso"] = "Resumen"
		st.rerun()



	if "messages" not in ss:
		ss["messages"] = [{"role": "assistant", "content": ss["pregunta1"]}]


	#st.title("Evaluación: " +ss["iso_seleccionada"])
	st.markdown(f"<h3>Clausula: {ss['nombreClausula']}</h3>", unsafe_allow_html=True)
	st.markdown(f"<h4>Categoría: {ss['nombreCategoria']}</h4>", unsafe_allow_html=True)
	st.markdown(f"<p style='margin-bottom: 60px;'>{ss['objetivoCategoria']}</p>", unsafe_allow_html=True)
	st.markdown(f"<h5>Control: {ss['nombreControl']}</h5>", unsafe_allow_html=True)
	st.subheader('Chat', divider='rainbow')


	# Imprime chat
	for msg in ss.messages:
		with st.chat_message(msg["role"]):
			st.write(msg["content"])

	
	
	# Respuesta
	if prompt := st.chat_input("Tu respuesta...",):
		if not openai_api_key:
			st.info("Please add your OpenAI API key to continue.")
			st.stop()
			
		#openai.api_key = openai_api_key
		ss.messages.append({"role": "user", "content": prompt})
		
		with st.chat_message("user"):
			st.write(prompt)
		
		with st.chat_message("assistant"):
			with st.spinner("Analizando..."):
				# llamando al LLM
				chat_llm_chain = ss["chat_llm_chain"]
				with get_openai_callback() as cb: # para contar los tokens
					respuesta = chat_llm_chain.predict(human_input=prompt)
				ss["total_tokens"] += cb.total_tokens
				
				

				#respuesta_json = json.dumps(respuesta)


				# Convertir la cadena JSON a un objeto JSON (diccionario de Python)
				try:
					objetoJson = json.loads(respuesta)
					#st.write(objetoJson)
				except json.JSONDecodeError as e:
				    st.error(f"Error al decodificar JSON: {e}")
				except AttributeError as e:
				    st.error(f"Error de atributo: {e}")
				except Exception as e:
				    st.error(f"Ocurrió un error inesperado: {e}")


				
				pregunta = objetoJson["respuesta"]["Pregunta"]
				dudas = objetoJson["respuesta"]["Dudas"]
				nota = objetoJson["respuesta"]["Nota"]
				sugerencia = objetoJson["respuesta"]["Sugerencia"]
				resumen = objetoJson["respuesta"]["Resumen"]
				hallazgos = objetoJson["respuesta"]["Hallazgo"]

				#pregunta = "pregunta"
				#dudas = "N"
				#nota = 7
				#sugerencia = "sugerencia"
				#resumen = "resumen"

				
				if dudas=="N":
					ss["messages"] = []
					
					# guardamos el resultado
					for iso, info in preguntasIsos.items():
						if ss["iso_seleccionada"] == iso :
							for clausula in info["Clausula"]:
								if clausula['Nombre'] == ss["nombreClausula"]:
									for categoria in clausula["Categorias"]:
										if categoria['Nombre'] == ss["nombreCategoria"]:
											for control in categoria["Control"]:
												if control['Nombre'] == ss["nombreControl"]:
													control['sugerencia'] = sugerencia
													control['resumen'] = resumen
													control['hallazgos'] = hallazgos
													control['nota'] = nota
													control['Impresa'] = "true"
													cleanVariablesSesion()
					ss["preguntasIsos"] = preguntasIsos
					#time.sleep(10)
					st.rerun()
				else:
					ss.messages.append({"role": "assistant", "content": pregunta})
					st.write(pregunta)

### Fin Chat ###
###########################



###############
### Resumen ###
if ss["proceso"] == "Resumen":
	#st.write(preguntasIsos)
	
	#del st.session_state["detalleResumen"]
	if "Resumen" not in ss:
		ss["Resumen"] = ""
	if "detalleResumen" not in ss:
		ss["detalleResumen"] = []
		
	col1, col2 = st.columns([3, 1])
	if col2.button("Salir", type="primary", help="Se eliminarán todos los datos ¿desea continuar?"):
		ss["proceso"] = "NivelEvaluacion"
		del st.session_state["Resumen"]
		del st.session_state["detalleResumen"]
		st.rerun()

	st.title("Evaluación de Riesgos Tecnológicos")
	st.subheader(ss["iso_seleccionada"])
	st.write(" ")
	st.write(" ")
	st.write(" ")
	

	#tab1, tab2 = st.tabs(["Resumen", "Detalles"])


	
	# Tab Resumen
	#with tab1:
	if ss["Resumen"] == "":
		preguntasRespuestas = getControlRespuestas()
		if preguntasRespuestas != "":
			with st.spinner("Espere un momento, estamos analizando sus respuestas..."):
				ss["Resumen"] = generar_resumen(openai_api_key, preguntasRespuestas)
		else:
			ss["Resumen"] = "No se cuenta con información para analizar."
	
	st.subheader("Clausulas Evaluadas")
	for clausulas in ss["options_clausulas"]:
		st.write("- "+clausulas)
	st.write(" ")
	st.write(" ")
	st.write(" ")
	
	st.subheader("Resumen Ejecutivo")
	st.write(ss["Resumen"])
	st.write(" ")
	st.write(" ")
	st.write(" ")
	
	
	
	# Tab Detalle 
	#with tab2:
	with st.spinner("Ya queda poco, danos un momento..."):
		pregRespDominio=""
		nota = 0
		Sugerencias=""
		Hallazgos=""
		k=0
		descripcionNota=""
		for iso, info in preguntasIsos.items():
			if ss["iso_seleccionada"] == iso :
				for clausula in info["Clausula"]:
					if clausula['Aplica'] == "true":
						st.markdown(f"""
						<div style='background-color: rgb(227 227 227);padding: 10px;margin-bottom: 20px;'>
							<h3>Clausula: {clausula['Nombre']}</h3>
						</div>
						""", unsafe_allow_html=True)
						for categoria in clausula["Categorias"]:
							if categoria['Aplica'] == "true":
								st.markdown(f"""
								<div style='background-color: none;padding: 10px;margin-bottom: 20px;'>
									<h5>Categoria: {categoria['Nombre']}</h5>
								</div>
								""", unsafe_allow_html=True)
								for control in categoria["Control"]:
									if control["Impresa"] == "true":
										st.markdown(f"""
										<div style='background-color: #f2f2f2;padding: 10px;margin-bottom: 20px;'>
		  									<p style='margin-top: 5px;'><b>{control["Nombre"]}</b></p>
											<p style='margin-top: 5px;'><b>Objetivo Control:</b> {control["Control"]}</p>
											<p style='margin-top: 5px;'><b>Resumen:</b> {control["resumen"]}</p>
											<p style='margin-top: 5px;'><b>Hallazgos:</b> {control["hallazgos"]}</p>
											<p style='margin-top: 5px;'><b>Sugerencias:</b><br>{control["sugerencia"]}</p>
										</div>
										""", unsafe_allow_html=True)


	#st.write("Total Tokens: ", ss["total_tokens"]) 
### FIN Resumen ###
###################
