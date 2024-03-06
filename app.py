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
        	SystemMessage(content="El texto que envia el usuario son preguntas y respuestas de una entrevista de auditoría. Resume el siguiente texto de manera muy formal y elimina las redundancias:"), # Mensaje persistente del 
		])
    
	llm = ChatOpenAI(temperature=0.5, openai_api_key = api_key, model="gpt-4")
	chat_llm_chain = LLMChain(
        	llm=llm,
        	prompt=prompt,
        	verbose=False,
    	)
	respuesta=chat_llm_chain.predict(human_input=texto)
	return respuesta

def contextoModelo(ISO, dominio, pregunta, otrasPreguntas):
	return f"""
 Tu rol será de Auditor Informático y deberás revisar el nivel de seguridad de la información de la empresa en relación a la siguiente pregunta obtenida de la {ISO}, del dominio {dominio}, y la pregunta es:
 <<{pregunta}>>

 El usuario comenzará respondiendo esta pregunta, pero si no te queda claro su respuesta o no abarca bien la pregunta, deberás consultar tus dudas o lo que sea necesario para poder analizar el nivel de seguridad en relación a esa pregunta. No hagas preguntas sobre:
 <<{otrasPreguntas}>>

 La salida deberá ser siempre en el siguiente formato:
 {{"respuesta": {{
	 "Dudas":"<<Si quedas con dudas en la respuesta del usuario responde 'S', si quedas conforme responde 'N'>>",
	 "Pregunta":"<<Solo si en el item dudas la respuesta es 'S', deberás incorporar tu nueva consulta acá, si no entonces responde ''>>",
  	 "Nota":"<<Solo si en el item dudas la respuesta es 'N', deberás evaluar el nivel de seguridad de 1 a 10, siendo el 1 el peor nivel y 10 el óptimo>>",
  	 "Resumen":"<<Solo si en el item dudas la respuesta es 'N', deberás realizar un breve resumen de la respuesta solo con lo más importante>>",
  	 "Hallazgo":"<<Solo si en el item dudas la respuesta es 'N' y si en el item 'nota' es menor o igual a 7, deberás redactar solo si existen los hallazgos de auditoría, sino entonces responde ''>>",
	 "Sugerencia":"<<Solo si en el item 'dudas' la respuesta es 'N' y si en el item 'nota' es menor o igual a 7, agrega tu sugerencia de auditoría a la observación, sino entonces responde ''>>"
 }}
 }}"""


def activaPreguntas (preguntasIsos):
	# Recorrer los dominios y preguntas y analiza cual toca preguntar
	for iso, info in preguntasIsos.items():
		if ss["iso_seleccionada"] == iso :
			for dominio in info["dominios"]:
				if dominio['nombre'] in ss["options_dominios"]:
					cantidadPreguntas = len(dominio["preguntas"])
					i=0
					salir = False
					for pregunta in dominio["preguntas"]:
						i+=1
						if i > cantidadPreguntas*ss["nivel_evaluacion"]/10:
							pregunta['aplica'] = "false"
				else:
					dominio['aplica'] = "false"
					for pregunta in dominio["preguntas"]:
						pregunta['aplica'] = "false"
	return preguntasIsos

def buscarPregunta (preguntasIsos):
	nombreDominio = ""
	descripcionDominio = ""
	preguntaStr = ""
	otrasPreguntas = ""
	
	# Recorrer los dominios y preguntas y analiza cual toca preguntar
	for iso, info in preguntasIsos.items():
		if ss["iso_seleccionada"] == iso :
			for dominio in info["dominios"]:
				if dominio['aplica'] == "true":
					nombreDominio = dominio["nombre"]
					descripcionDominio = dominio["descripcion"]
					i=0
					for pregunta in dominio["preguntas"]:
						if pregunta["aplica"] == "true" and pregunta["impresa"] == "false":
							i += 1
							if i == 1: # obtiene la primera pregunta que encuentra
								preguntaStr = pregunta["texto"]
							else:
								otrasPreguntas += pregunta['texto']+" "
					if i > 0:
						break
	
	return nombreDominio, descripcionDominio, preguntaStr, otrasPreguntas

def desactivarPregunta (preguntasIsos, nombreDominio, preguntaStr, tipo):
	borradoCorrecto = False
	for iso, info in preguntasIsos.items():
		if ss["iso_seleccionada"] == iso :
			for dominio in info["dominios"]:
				if dominio["nombre"] == nombreDominio:
					for pregunta in dominio["preguntas"]:
						if pregunta["texto"] == preguntaStr:
							if tipo == "aplica":
								pregunta["aplica"] = "false"
								borradoCorrecto = True
							if tipo == "impresa":
								pregunta["impresa"] = "true"
								borradoCorrecto = True
							break
	return borradoCorrecto

def cleanVariablesSesion():
	ss["nombreDominio"] = ""
	ss["descripcionDominio"] = ""
	ss["pregunta"] = ""
	ss["otrasPreguntas"] = ""
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


def getPreguntasRespuestas():
	pregRespDominio = ""
	for iso, info in preguntasIsos.items():
		if ss["iso_seleccionada"] == iso :
			for dominio in info["dominios"]:
				if dominio["aplica"] == "true":
					for pregunta in dominio["preguntas"]:
						if pregunta["impresa"] == "true" and pregunta["aplica"] == "true":
							pregRespDominio += pregunta['texto']+" "+pregunta['resumen']+"\n"

	return pregRespDominio


#####################################
# __main__


#Inicializar general
ss = st.session_state
if "proceso" not in ss:
	ss["proceso"] = "NivelEvaluacion"
if "options_dominios" not in ss:
	ss["options_dominios"] = []
if "nombreDominio" not in ss:
	ss["nombreDominio"] = ""
if "descripcionDominio" not in ss:
	ss["descripcionDominio"] = ""
if "pregunta" not in ss:
	ss["pregunta"] = ""
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
mostrarBarra = True
if "lkn" in params:
	if params["lkn"][0] == "view":
		mostrarBarra = False

if mostrarBarra:	
	with st.sidebar:
	    #openai_api_key = st.text_input("OpenAI API Key", key="chatbot_api_key", type="password")
	    st.sidebar.header('Evaluador de Riesgos Tecnológicos')
	    st.markdown("""
	        <div style="text-align: justify;">
	            Bienvenido al asistente IA de evaluación de riesgos tecnológicos. Este chatbot está diseñado para guiarlo en una encuesta de evaluación, la cual permitirá conocer deficiencias en su organización relacionadas a la seguridad de la información. Finalmente, el sistema procesará la información y entregará el resultado del análisis realizado. Conteste las preguntas con honestidad.
	        </div>
	    """, unsafe_allow_html=True)
	    st.text("")
	    st.sidebar.header('Aplicación creada por \n')
	    "[Víctor Vásquez](https://www.linkedin.com/in/victorvasquezrivas/)"
	    "[victorvasquezrivas@gmail.com](mailto:victorvasquezrivas@gmail.com)"

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
	
	# Acceder a los dominios de la ISO especificada
	dominios = const.isos[iso_seleccionada]["dominios"]
	# Extraer los nombres de los dominios
	nombres_dominios = [dominio["nombre"] for dominio in dominios]
	options_dominios = st.multiselect('Seleccione el dominio:',nombres_dominios,placeholder="Agregue todos los dominio que evaluará")

	st.write(" ")
	st.write(" ")
	
	# Selección del nivel de evaluación
	nivel_evaluacion = st.slider("Seleccione el nivel de profundidad en la evaluación", min_value=1, max_value=10, value=10)
	st.info(f"La cantidad de tiempo aproximado en la evaluación será de : {str(round(150*(nivel_evaluacion/10)*len(options_dominios)/11))} minutos")

	st.write(" ")
	st.write(" ")
	
	# Btn Aceptar nivel evaluación
	if st.button('Evaluar'):
		if len(options_dominios) == 0:
			st.warning('Debe seleccionar al menos 1 dominio', icon="⚠️")
		else:
			ss["proceso"] = "Chat"
			ss["nivel_evaluacion"] = nivel_evaluacion
			ss["iso_seleccionada"] = iso_seleccionada
			ss["options_dominios"] = options_dominios
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
	if ss["pregunta"] == "":
		ss["nombreDominio"],ss["descripcionDominio"], ss["pregunta"], ss["otrasPreguntas"] = buscarPregunta(preguntasIsos)
		nombreISO = ""
		for iso, info in preguntasIsos.items():
			if ss["iso_seleccionada"] == iso :
				nombreISO = info["nombreIso"]
		ss["chat_llm_chain"] = modeloMemoryLangChainOpenAI(openai_api_key, "gpt-4", contextoModelo(nombreISO, ss["nombreDominio"], ss["pregunta"], ss["otrasPreguntas"]))

	
	# Ya no quedan más preguntas
	if ss["pregunta"] == "": 
		ss["proceso"] = "Resumen"
		st.rerun()



	if "messages" not in ss:
		ss["messages"] = [{"role": "assistant", "content": ss["pregunta"]}]


	st.title("Evaluación: " +ss["iso_seleccionada"])
	st.markdown(f"<h3>Dominio: {ss['nombreDominio']}</h3>", unsafe_allow_html=True)
	st.markdown(f"<p style='margin-bottom: 60px;'>{ss['descripcionDominio']}</p>", unsafe_allow_html=True)
	st.subheader('Chat', divider='rainbow')

	col1, col2 = st.columns([3, 1])
	if col2.button("No aplica pregunta", type="primary", help="Esta pregunta no aplica a su organización, por lo que se eliminará"):
		if desactivarPregunta (preguntasIsos, ss["nombreDominio"], ss["pregunta"], "aplica"):
			cleanVariablesSesion()
			time.sleep(5)
			st.rerun()
		else:
			st.write("No se pudo desactivar pregunta, intente nuevamente")


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
				
				
				objetoJson = json.loads(respuesta)
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
							for dominio in info["dominios"]:
								if dominio['nombre'] == ss["nombreDominio"]:
									for pregunta in dominio["preguntas"]:
										if pregunta['texto'] == ss["pregunta"]:
											pregunta['sugerencia'] = sugerencia
											pregunta['resumen'] = resumen
											pregunta['hallazgos'] = hallazgos
											pregunta['nota'] = nota
											pregunta['impresa'] = "true"
											cleanVariablesSesion()
					ss["preguntasIsos"] = preguntasIsos
					#time.sleep(10)
					st.rerun()
				else:
					ss.messages.append({"role": "assistant", "content": pregunta})
					st.write(pregunta)

### Fin Chat ###
###########################


#if ss["proceso"] == "Resumen":
#	st.title("Resumen")
#	if st.button("Volver a chat"):
#		ss["proceso"] = "Chat"

#st.stop()

###############
### Resumen ###
if ss["proceso"] == "Resumen":
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
	
	st.title("Resultado: " +ss["iso_seleccionada"])
	
	with st.spinner("Espere un momento, estamos analizando sus respuestas..."):

		#tab1, tab2 = st.tabs(["Resumen", "Detalles"])

		# Tab Resumen
		#with tab1:
		if ss["Resumen"] == "":
			preguntasRespuestas = getPreguntasRespuestas()
			ss["Resumen"] = generar_resumen(openai_api_key, preguntasRespuestas)
		
		st.subheader("Dominios Evaluados")
		for dominio in ss["options_dominios"]:
			st.write("- "+dominio)
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
		if len(ss["detalleResumen"]) == 0:
			pregRespDominio=""
			nota = 0
			Sugerencias=""
			Hallazgos=""
			k=0
			descripcionNota=""
			for iso, info in preguntasIsos.items():
				if ss["iso_seleccionada"] == iso :
					for dominio in info["dominios"]:
						if dominio["aplica"] == "true":
							nota=0
							i=0
							j=0
							pregRespDominio=""
							Sugerencias=""
							Hallazgos=""
							for pregunta in dominio["preguntas"]:
								if pregunta["impresa"] == "true" and pregunta["aplica"] == "true":
									pregRespDominio += pregunta['texto']+" "+pregunta['resumen']+"<br>"
									if pregunta['nota'].isdigit(): #devuelve True para cadenas que contienen dígitos del 0 al 9
										nota += int(pregunta['nota'])
										i+=1
										
									if pregunta['sugerencia'] != "":
										j+=1
										Hallazgos += str(j)+".- "+ pregunta['hallazgos'] + "<br>"
										Sugerencias += str(j)+".- "+ pregunta['sugerencia'] + "<br>"
										
										
							# query a modelo para realizar resumen
							resumen = generar_resumen(openai_api_key, pregRespDominio)
							if i == 0:
								i = 1
							notaFinal = str(round(nota/i))
							
							if round(nota/i) <= 2:
								descripcionNota = "Insuficiente"
							elif round(nota/i) > 2 and round(nota/i) <=4:
								descripcionNota = "Baja"
							elif round(nota/i) > 4 and round(nota/i) <=6:
								descripcionNota = "Regular"
							elif round(nota/i) > 6 and round(nota/i) <=8:
								descripcionNota = "Bien"
							else:
								descripcionNota = "Excelente"
							
							if j==0:
								Sugerencias="No se han determinado sugerencias"
								Hallazgos="No se han determinado hallazgos"
								
							nueva_fila = [
								{"dominio": dominio["nombre"], "notaFinal": notaFinal, "descripcionNota": descripcionNota, "resumen": resumen, "Hallazgos": Hallazgos, "Sugerencias": Sugerencias, "preguntasRespuestas":pregRespDominio}
							]
							ss["detalleResumen"].append(nueva_fila)

							k += 1
	
		for elemento in ss["detalleResumen"]:
			st.markdown(f"""
			<div style='background-color: rgb(227 227 227);padding: 10px;margin-bottom: 20px;'>
				<h3>Dominio: {elemento[0]["dominio"]}</h3>
			</div>
			""", unsafe_allow_html=True)
			st.markdown(f"""
			<div style='background-color: #f2f2f2;padding: 10px;margin-bottom: 20px;'>
				<p style='margin-top: 5px;'><b>Nota:</b> {elemento[0]["notaFinal"]} ({elemento[0]["descripcionNota"]})</p>
				<p style='margin-top: 5px;'><b>Resumen:</b> {elemento[0]["resumen"]}</p>
				<p style='margin-top: 5px;'><b>Hallazgos:</b> {elemento[0]["Hallazgos"]}</p>
				<p style='margin-top: 5px;'><b>Sugerencias:</b><br>{elemento[0]["Sugerencias"]}</p>
			</div>
			""", unsafe_allow_html=True)
			with st.expander("Preguntas Realizadas"):
				st.markdown(f"""
				<div style='background-color: #f2f2f2;padding: 10px;margin-bottom: 20px;'>
					<p style='margin-top: 5px;'>{elemento[0]["preguntasRespuestas"]}</p>
				</div>
				""", unsafe_allow_html=True)


	#st.write("Total Tokens: ", ss["total_tokens"]) 
### FIN Resumen ###
###################
