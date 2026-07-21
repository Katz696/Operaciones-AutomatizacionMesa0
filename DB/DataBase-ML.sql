--
-- PostgreSQL database dump
--

\restrict DesEX0Vb8aTQkVnBxHPuU0DthzfeK4eK5XKz6ZYLI4ORUszHxzvwHqlXZ3AEeYo

-- Dumped from database version 15.17 (Debian 15.17-1.pgdg13+1)
-- Dumped by pg_dump version 18.1

-- Started on 2026-06-09 12:58:48

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 216 (class 1259 OID 34571)
-- Name: api_users; Type: TABLE; Schema: public; Owner: ml_user
--

CREATE TABLE public.api_users (
    id integer NOT NULL,
    username text NOT NULL,
    password_hash text NOT NULL,
    is_active boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.api_users OWNER TO ml_user;

--
-- TOC entry 215 (class 1259 OID 34570)
-- Name: api_users_id_seq; Type: SEQUENCE; Schema: public; Owner: ml_user
--

CREATE SEQUENCE public.api_users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.api_users_id_seq OWNER TO ml_user;

--
-- TOC entry 3441 (class 0 OID 0)
-- Dependencies: 215
-- Name: api_users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: ml_user
--

ALTER SEQUENCE public.api_users_id_seq OWNED BY public.api_users.id;


--
-- TOC entry 218 (class 1259 OID 34933)
-- Name: models; Type: TABLE; Schema: public; Owner: ml_user
--

CREATE TABLE public.models (
    id integer NOT NULL,
    nombre character varying(255),
    version character varying(50),
    archivo character varying(255),
    accuracy double precision,
    f1_score double precision,
    fecha_entrenamiento timestamp without time zone,
    activo boolean DEFAULT false,
    notas text
);


ALTER TABLE public.models OWNER TO ml_user;

--
-- TOC entry 217 (class 1259 OID 34932)
-- Name: models_id_seq; Type: SEQUENCE; Schema: public; Owner: ml_user
--

CREATE SEQUENCE public.models_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.models_id_seq OWNER TO ml_user;

--
-- TOC entry 3442 (class 0 OID 0)
-- Dependencies: 217
-- Name: models_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: ml_user
--

ALTER SEQUENCE public.models_id_seq OWNED BY public.models.id;


--
-- TOC entry 214 (class 1259 OID 26282)
-- Name: tickets_feedback; Type: TABLE; Schema: public; Owner: ml_user
--

CREATE TABLE public.tickets_feedback (
    id text NOT NULL,
    incident_title text,
    description text,
    padtypes_id_predicho text,
    tipo_predicho text,
    confianza double precision,
    fecha timestamp without time zone,
    ml_revision text,
    used_for_training boolean DEFAULT false,
    padtypes_id_corregido text
);


ALTER TABLE public.tickets_feedback OWNER TO ml_user;

--
-- TOC entry 3273 (class 2604 OID 34574)
-- Name: api_users id; Type: DEFAULT; Schema: public; Owner: ml_user
--

ALTER TABLE ONLY public.api_users ALTER COLUMN id SET DEFAULT nextval('public.api_users_id_seq'::regclass);


--
-- TOC entry 3276 (class 2604 OID 34936)
-- Name: models id; Type: DEFAULT; Schema: public; Owner: ml_user
--

ALTER TABLE ONLY public.models ALTER COLUMN id SET DEFAULT nextval('public.models_id_seq'::regclass);


--
-- TOC entry 3433 (class 0 OID 34571)
-- Dependencies: 216
-- Data for Name: api_users; Type: TABLE DATA; Schema: public; Owner: ml_user
--

COPY public.api_users (id, username, password_hash, is_active, created_at) FROM stdin;
1	admin	$2b$12$rHlUhACGks1T582R7PJ8eu0.V/p/m47eTIQGqJvonhAG4oAqhs1Wa	t	2026-03-25 22:14:32.015274
\.


--
-- TOC entry 3435 (class 0 OID 34933)
-- Dependencies: 218
-- Data for Name: models; Type: TABLE DATA; Schema: public; Owner: ml_user
--

COPY public.models (id, nombre, version, archivo, accuracy, f1_score, fecha_entrenamiento, activo, notas) FROM stdin;
5	clasificador_tickets	20260330_1846	modelo_tickets_20260330_1846.pkl	0.9285257713986868	0.9266573772743096	2026-03-30 18:52:34.130348	f	\N
2	clasificador_tickets	20260324_2320	modelo_tickets_20260324_2320.pkl	0.9285257713986868	0.9266573772743096	2026-03-28 00:38:43.187517	f	\N
7	clasificador_tickets	20260330_1856	modelo_tickets_20260330_1856.pkl	0.9285257713986868	0.9266573772743096	2026-03-30 19:59:26.600238	f	\N
1	Primer modelo	20260313_1839	modelo_tickets_20260313_1839.pkl	0.9296298448486258	0.9277000760215504	2026-03-30 18:48:58.499224	t	\N
12	clasificador_tickets	20260330_2335	modelo_tickets_20260330_2335.pkl	0.9292230809460166	0.9273791515566971	2026-03-30 23:38:25.126983	f	\N
\.


--
-- TOC entry 3431 (class 0 OID 26282)
-- Dependencies: 214
-- Data for Name: tickets_feedback; Type: TABLE DATA; Schema: public; Owner: ml_user
--

COPY public.tickets_feedback (id, incident_title, description, padtypes_id_predicho, tipo_predicho, confianza, fecha, ml_revision, used_for_training, padtypes_id_corregido) FROM stdin;
fb816726-2bec-475c-9d6b-82949cbb1dcb	Mesa Cero - Impresora con atasco de papel – en la impresora HP LaserJet M404	El sistema operativo reporta errores de lectura/escritura en disco. Impacto detectado: Bloquea la impresión de documentos del departamento. Acciones previas realizadas: El equipo fue reiniciado varias veces sin resultado. Se solicita intervención del equipo de soporte para resolución.	D937532B-6762-4521-9F60-254D2D2D8B2E	Incidente	0.5374390718085452	2026-05-16 00:48:17.24539	corregido	f	D937532B-6762-4521-9F60-254D2D2D8B2E
174d1e24-66e4-4331-b09f-a9bbb14907b9	4068-3 / GEY BAAS / Revision Warnings	Se detecto que los jobs en el portal Veam del cliente de Gobierno (GEY) muestra un warning (Virtual machine "Name_X" is unavailable and skkip). de backup	D937532B-6762-4521-9F60-254D2D2D8B2E	Incidente	0.7424014922320264	2026-05-25 23:04:40.226201	pendiente	f	\N
987b28b9-bcb6-42d6-9e99-79a1354a59b0	Proyecto Interno / Replicar las clasificaciones de las oportunidades de los proyectos a Proactivanet (Nelvy)	Buen día\n\nSe genera ticket para el registro de actividades de Nelvy Sima para el proyecto interno de Replicar las clasificaciones de las oportunidades de los proyectos a Proactivanet	C87AF0DB-319C-432A-8850-29F46FC36402	Requerimiento	0.5173614711795074	2026-05-25 23:04:40.521841	pendiente	f	\N
da7ef5e7-4bae-40b8-89c9-613b7a62a9cc	3472 / Enkontrol / Autenticacion cuentas enkontrol.cloud	Se ha presentado que en cuentas admin del dominio  enkontrol.cloud ha solcitado autenticación a un movil... y ya tmb se presento con una cuenta del un cliente\nEn el documento anexo vienen detalles.\nQue hay que hacer para EVITAR esta autenticación a travez de un movil	C87AF0DB-319C-432A-8850-29F46FC36402	Requerimiento	0.6435367252171486	2026-05-25 23:04:42.682999	pendiente	f	\N
94e836f2-905a-46cb-9727-bef432ad2322	3588-4 / Compañia Fernandez / Lentitud en SAP y Servicios	Buen día.\n\nSe levanta ticket, ya que se reporta que hay lentitud en SAP y en los servicios de Compañia Fernandez favor de validar.	D937532B-6762-4521-9F60-254D2D2D8B2E	Incidente	0.6926639110844053	2026-05-25 23:04:43.351357	pendiente	f	\N
cbd67746-8766-42e5-a7f1-d2039bf28881	Perfilamiento Express WEB SIR	Equipo buenas tardes solicito su apoyo debido a que en WEB SIR en los apartados Mesa de Control-Autofinanciamiento-Consulta al ingresar a los registros no aparece el botón perfilar después de que evaluación ya concluyo su proceso.\n\nEstoy atento a sus comentarios.\n\nSaludos.	C87AF0DB-319C-432A-8850-29F46FC36402	Requerimiento	0.5513764047391566	2026-05-25 23:04:43.373581	pendiente	f	\N
6a11ce81-d427-442d-8873-b2dd94a92b65	3435-4 / UNIR / Problema iniciar sesion correo	Se solicita apoyo para maestro \n\ndiego.islas@universidadriviera.mx  ya que no puede acceder a correo	C87AF0DB-319C-432A-8850-29F46FC36402	Requerimiento	0.5660019283317784	2026-03-25 00:42:25.895003	corregido	t	D937532B-6762-4521-9F60-254D2D2D8B2E
8e15b0f1-3d98-414a-915b-52bb14bbfc75	4637 / Petromayab / Acompañamiento Contabilidad Electronica	Buen día.\n\nSe levanta ticket para el registro de actividades de Fatima Cante para el acompañamiento de la configuración de Contabilidad Electronica para el cliente Petromayab	C87AF0DB-319C-432A-8850-29F46FC36402	Requerimiento	0.7410191034729665	2026-05-25 23:04:43.554496	pendiente	f	\N
4ff7c74f-47ed-4303-9304-141f290d6287	4388-1 / GEY / Portal Proactiva fuera de alcance	Buen día.\n\nSe levanta ticket, ya que en el Gobierno del Estado de Yucatán el portal de proactiva esta fuera de alcance	C87AF0DB-319C-432A-8850-29F46FC36402	Requerimiento	0.7092952733691299	2026-03-27 22:55:34.700003	corregido	t	OTROS
7bb7ddc8-9768-4490-8e82-f9467a8f62ee	Solicitud de Expediente Digital cliente 5719 - 020 MARTINEZ ALBARRAN RAFAEL	Buenas tardes.\n\nLes pido por favor su apoyo para el envio digital del expediente del cliente 5719 - 020 MARTINEZ ALBARRAN RAFAEL ya que no podemos visualizar imagenes en sistema.\n\nBID;041 ,  CMAMERICAS, S.A. DE C.V.\n\nGracias	C87AF0DB-319C-432A-8850-29F46FC36402	Requerimiento	0.7971253647402236	2026-03-27 22:55:34.7059	confirmado	t	C87AF0DB-319C-432A-8850-29F46FC36402
0f816073-417c-4fbd-95da-bc3a3ab92c7f	Error al subir layout de pago por Openpay	Hola...\n\nSe recibio un pago por medio de Openpay, se subio de manera correcta a Progress, pero se va a cobranza rechazada cuando tiene grupo intengrante asignado (5828-015), podrian revisar el porque se esta registrando mal xfis, anexo el archivo de layout que nos da el portal de Openpay...\n\n\n\n\n\n\n\n\n\n\n\n\n\nGracias de antemano...\n\nNOTA: Pasar el ticket a Cesar Cruz, el esta llevando este caso...\n\nSaludos...\nAnali A.	D937532B-6762-4521-9F60-254D2D2D8B2E	Incidente	0.5589210981653254	2026-03-27 22:20:47.471129	confirmado	t	D937532B-6762-4521-9F60-254D2D2D8B2E
d2a917ec-833d-4fc9-90a7-6d2708eb1a7f	Ayuda con correos	Buenos días\n\nEstimados, por favor requiero de su valiosa ayuda para verificar mi correo, ya que no me están llegando, adicionas únicamente entran muchos de prueba, pero los correos vigentes de hoy no me llegan (jvelazquezm@conauto.mx).\n\nGracias y saludos.	D937532B-6762-4521-9F60-254D2D2D8B2E	Incidente	0.7473870440965737	2026-03-27 22:55:34.349883	confirmado	t	D937532B-6762-4521-9F60-254D2D2D8B2E
1658c837-d541-490f-ae85-a4453d152b71	GRUPO INTEGRANTE 8487-017	Hola buenos dias, me pueden ayudar de favor a que se acepte mi aceptacion digital.\nNo me da otro grupo integrante.\n\n\nLA RUTA ES:\nMENU GENERAL CON CLAVE INT \nCONTROL VALIJA \nRECEPCION\nCONTROL VALIJA	D937532B-6762-4521-9F60-254D2D2D8B2E	Incidente	0.5134321609777608	2026-04-20 18:48:43.918708	confirmado	f	D937532B-6762-4521-9F60-254D2D2D8B2E
6e25edb0-e8c5-4ee0-b812-89eb2f5fb126	GRUPO INTEGRANTE 8486-022	Hola buenos dias, me pueden ayudar de favor a que se acepte en el sistema la aceptacion digital en el sir.\nNo me da otro grupo integrante.\n\n\n\nLA RUTA ES MENU GENRAL CO CLAVE INT \nCONTROL VALIJA \nRECEPCION\nCONTROL VALIJA	D937532B-6762-4521-9F60-254D2D2D8B2E	Incidente	0.49560121433193544	2026-04-20 18:48:43.814306	enviado	f	\N
177c3f04-972d-4c91-b1f6-0d1ddb545ace	FALLAS EN IMPRESORA PISO 6	\N	D937532B-6762-4521-9F60-254D2D2D8B2E	Incidente	0.7034680807496901	2026-05-14 19:50:19.12873	enviado	f	\N
b103f45f-29c5-4d37-8678-d1d07f44c100	RECOVE WEB GC	\N	C87AF0DB-319C-432A-8850-29F46FC36402	Requerimiento	0.6411549027699264	2026-05-14 19:50:19.212925	enviado	f	\N
1a829f95-183e-4b53-9abc-4021a29f0829	GCTI / You have alerts on your managed domain	Favor de revisar y atender\n\nSaludos\n\nRoger Guevara González\nDirector\n\n[cid:image001.jpg@01D6BBF2.83B7D130]\nCel.  (999) 955.17.80\nrogerg@gconsultores.com.mx\nwww.gconsultores.com.mx<http://www.gconsultores.com.mx>\n\n\n\nDe: Microsoft Security <MSSecurity-noreply@microsoft.com>\nFecha: lunes, 11 de mayo de 2026, 10:13 a.m.\nPara: Roger Guevara Gonzalez <rogerg@Gconsultores.com.mx>\nAsunto: You have alerts on your managed domain\n\n[Microsoft Security]\nYou have alerts on your managed domain\n\nWe detected critical or warning alerts on your Microsoft Entra Domain Services managed domain, gconsultores.com.mx, on May 11, 2026 15:26 UTC. These issues may negatively affect your service—please resolve them as soon as possible.\n\nTo see your alerts and check the health of your managed domain, visit the Health page on the Azure portal<https://nam.safelink.emails.azure.net/redirect/?destination=https%3A%2F%2Fportal.azure.com%2F&p=bT02ZDgxYjJjNi01NGViLTRhYTktOTQ1MS1iMTNmNDliOTY5ZWMmdT1hZW8mbD1wb3J0YWwuYXp1cmUuY29t>, or click the button below.\n\nView and resolve these alerts ><https://nam.safelink.emails.azure.net/redirect/?destination=https%3A%2F%2Fportal.azure.com%2F%23%40c164b766-3480-40cc-87af-416efc8b4773%2Fresource%2F%2Fsubscriptions%2Fb969cb8e-ff5f-4fcd-90d2-f8ca8422782b%2FresourceGroups%2Frg-gcti-adds%2Fproviders%2FMicrosoft.AAD%2FdomainServices%2Fgconsultores.com.mx%2FhealthReporting&p=bT02ZDgxYjJjNi01NGViLTRhYTktOTQ1MS1iMTNmNDliOTY5ZWMmdT1hZW8mbD1wb3J0YWwuYXp1cmUuY29tXzI%3D>\nWhy am I receiving this email?\n\nYour email is set up to receive Microsoft Entra Domain Services notifications about your managed domain, gconsultores.com.mx. You may edit your notification settings<https://nam.safelink.emails.azure.net/redirect/?destination=https%3A%2F%2Fportal.azure.com%2F%23%40c164b766-3480-40cc-87af-416efc8b4773%2Fresource%2F%2Fsubscriptions%2Fb969cb8e-ff5f-4fcd-90d2-f8ca8422782b%2FresourceGroups%2Frg-gcti-adds%2Fproviders%2FMicrosoft.AAD%2FdomainServices%2Fgconsultores.com.mx%2FnotificationSettings&p=bT02ZDgxYjJjNi01NGViLTRhYTktOTQ1MS1iMTNmNDliOTY5ZWMmdT1hZW8mbD1wb3J0YWwuYXp1cmUuY29tXzM%3D> on the Azure portal any time.\n\nWhy are there no alerts on my Health page?\n\nManaged domains are checked for alerts every hour. If an alert is resolved, then it disappears from the Health page on the Azure portal. If there are no alerts visible, it could be that someone else resolved your alert or it had been automatically resolved.\n\nDid you find this email helpful? Yes<https://nam.safelink.emails.azure.net/trackingfeedback/?p=bT02ZDgxYjJjNi01NGViLTRhYTktOTQ1MS1iMTNmNDliOTY5ZWMmZj1Qb3NpdGl2ZSZiPWVuLXVzJmE9NS8xMS8yMDI2IDQ6MTM6MDQgUE0mdT1hZW8%3D> No<https://nam.safelink.emails.azure.net/trackingfeedback/?p=bT02ZDgxYjJjNi01NGViLTRhYTktOTQ1MS1iMTNmNDliOTY5ZWMmZj1OZWdhdGl2ZSZiPWVuLXVzJmE9NS8xMS8yMDI2IDQ6MTM6MDQgUE0mdT1hZW8%3D>\n\n[Facebook]<https://nam.safelink.emails.azure.net/redirect/?destination=https%3A%2F%2Fwww.facebook.com%2Fmicrosoftazure&p=bT02ZDgxYjJjNi01NGViLTRhYTktOTQ1MS1iMTNmNDliOTY5ZWMmdT1hZW8mbD1mb290ZXIlM0FmYWNlYm9vaw%3D%3D>  [Twitter] <https://nam.safelink.emails.azure.net/redirect/?destination=https%3A%2F%2Ftwitter.com%2Fazure&p=bT02ZDgxYjJjNi01NGViLTRhYTktOTQ1MS1iMTNmNDliOTY5ZWMmdT1hZW8mbD1mb290ZXIlM0F0d2l0dGVy>        [YouTube] <https://nam.safelink.emails.azure.net/redirect/?destination=https%3A%2F%2Fwww.youtube.com%2F%40MicrosoftAzure&p=bT02ZDgxYjJjNi01NGViLTRhYTktOTQ1MS1iMTNmNDliOTY5ZWMmdT1hZW8mbD1mb290ZXIlM0F5b3V0dWJl>        [LinkedIn] <https://nam.safelink.emails.azure.net/redirect/?destination=https%3A%2F%2Fwww.linkedin.com%2Fshowcase%2Fmicrosoft-developers&p=bT02ZDgxYjJjNi01NGViLTRhYTktOTQ1MS1iMTNmNDliOTY5ZWMmdT1hZW8mbD1mb290ZXIlM0FsaW5rZWRpbg%3D%3D>\n\nPrivacy Statement<https://nam.safelink.emails.azure.net/redirect/?destination=https%3A%2F%2Fgo.microsoft.com%2Ffwlink%2F%3FLinkId%3D521839&p=bT02ZDgxYjJjNi01NGViLTRhYTktOTQ1MS1iMTNmNDliOTY5ZWMmdT1hZW8mbD1wcml2YWN5LXN0YXRlbWVudA%3D%3D>\n\nMicrosoft Corporation, One Microsoft Way, ​Redmond, WA 98052​\n\n[Microsoft]\n[https://nam.safelink.emails.azure.net/trackingpixel/?p=bT02ZDgxYjJjNi01NGViLTRhYTktOTQ1MS1iMTNmNDliOTY5ZWMmdT1hZW8%3D]\n	C87AF0DB-319C-432A-8850-29F46FC36402	Requerimiento	0.631401007177173	2026-05-14 19:50:18.998321	enviado	f	\N
5c5244fc-7056-4e68-a081-459489e6981e	ticket de prueba desde API	prueba de creacion de ticket desde API de proactiva	C87AF0DB-319C-432A-8850-29F46FC36402	Requerimiento	0.39053318875374216	2026-05-16 00:48:17.246544	confirmado	f	C87AF0DB-319C-432A-8850-29F46FC36402
df1eba10-b21c-4a1b-8826-ce8e259caf00	NO SE PODIA VISUALIZAR EL ESTADO DE CUENTA EN SOFOM	Buen dia:\n\nNo se podía visualizar el estado de cuenta en SOFOM, por lo cual el Ing. David  Maqueda, me apoyo a  crear la carpeta \n\nscreenvi\n\nYa puedo visualizar.\n\nmuchas gracias	D937532B-6762-4521-9F60-254D2D2D8B2E	Incidente	0.7040204291370689	2026-05-25 23:04:40.201164	pendiente	f	\N
ad434988-971e-4a0a-bcf2-dbed171ba8de	Proyecto Interno / Replicar las clasificaciones de las oportunidades de los proyectos a Proactivanet (Gloria)	Buen día\n\nSe genera ticket para el registro de actividades de Gloria Medina para el proyecto interno de Replicar las clasificaciones de las oportunidades de los proyectos a Proactivanet	OTROS	Otros	0.5766757442112957	2026-05-25 23:04:40.602644	pendiente	f	\N
8732299c-a657-4ac4-ac7d-a96fb0d1a6ce	RE: ERROR DE CONTRASEÑA	Me pueden apoyar por favor \n\n \n\n...todo en un solo lugar Ford Rivera Serdan  <http://fordrivera.mx/> \n\n \n\n\n\n \n\nLaura Hernandez\n\nConauto\n\nRivera Serdan\n\nBoulevard Hermanos Serdán N°. 235\n\nColonia Aquiles Serdán, 72140, Ciudad de Puebla, Puebla.\n\nCP 72140\n\nTel: 222 689 3333\n\nsegurosc@fordserdan.com.mx <mailto:segurosc@fordserdan.com.mx> \n\n \n\n“Le informamos que sus datos están protegidos conforme a  la Ley Federal de\nProtección de Datos Personales en Posesión de Particulares.\n\nPuede consultar nuestro Aviso de Privacidad en  <https://www.fordrivera.mx/>\nhttps://www.fordrivera.mx/”\n\n \n\nDe: Laura Hernandez - Conauto Serdan [mailto:segurosc@fordserdan.com.mx] \nEnviado el: martes, 19 de mayo de 2026 06:25 p. m.\nPara: 'Solicitudes@gconsultores.com.mx'\nAsunto: ERROR DE CONTRASEÑA \n\n \n\nBuenas tardes\n\nme apoyan con mi contraseña puesto que no la he cambiado y me marca error de\ncontraseña en ESOF12 \n\nESOF12 USUARIO: LHS320\n\n \n\n \n\n...todo en un solo lugar Ford Rivera Serdan  <http://fordrivera.mx/> \n\n \n\n\n\n \n\nLaura Hernandez\n\nConauto\n\nRivera Serdan\n\nBoulevard Hermanos Serdán N°. 235\n\nColonia Aquiles Serdán, 72140, Ciudad de Puebla, Puebla.\n\nCP 72140\n\nTel: 222 689 3333\n\nsegurosc@fordserdan.com.mx <mailto:segurosc@fordserdan.com.mx> \n\n \n\n“Le informamos que sus datos están protegidos conforme a  la Ley Federal de\nProtección de Datos Personales en Posesión de Particulares.\n\nPuede consultar nuestro Aviso de Privacidad en  <https://www.fordrivera.mx/>\nhttps://www.fordrivera.mx/”\n\n \n\n	C87AF0DB-319C-432A-8850-29F46FC36402	Requerimiento	0.705003263584721	2026-05-25 23:04:43.329555	pendiente	f	\N
eaca09fe-c483-442b-a3ba-2e850c9efa98	GCTI / APOYO CON EQUIPO LENTO	EL EQUIPO PRESENTA INICIO O CARGA TARDÍA, SE REINICIA EN VARIAS OCASIONES TENIENDO EL MISMO RESULTADO. \n\nSE SOLICITA APOYO.	C87AF0DB-319C-432A-8850-29F46FC36402	Requerimiento	0.5453017802378518	2026-05-25 23:04:43.381857	pendiente	f	\N
e34b3f13-1f57-4fe3-858a-f3909c4d50ad	4693 / Enkontrol / ALFAVENT / Incidencia en cuenta de usuario	Nos pueden ayudar a revisar la cuenta alf.lvazquez@enkontrol.cloud, nos esta reportando el cliente que al ingresar no le aparecen las aplicaciones.\n\nSaldo en puntos: 1552vigencia del contrato: 11/08/2024	D937532B-6762-4521-9F60-254D2D2D8B2E	Incidente	0.5145334074910477	2026-05-25 23:04:43.498135	pendiente	f	\N
1830530b-6915-49c1-bcb0-47a4ca848a2a	4239-3 / BEPENSA / Programar tareas de encendido y apagados de MV.	Estimado GConsultores, favor de configurar las siguientes reglas de encendido y apagado a las sig. MV, adicional necesito que se envié notificación de las actividades de encendido y apagado  al email (avalencia@bepensa.com<mailto:avalencia@bepensa.com>)\n\nMV: VCDAZRPADOM-01\n\n  *   Encender: solo los miércoles en horario de 9:00 AM a 2:00 PM\n  *   Apagar el resto de los días.\n\nMV: VCPAZRPADOM-01\n\n  *   Encender: de L a V de (5:00 AM a 11:00 PM)\n  *   Apagar: de L a V deberá estar apagada de 10:59  PM a 4:59 AM (sábados y domingo deberá permanecer apagada)\n\nMV: VFDAZAPPZAP03-V2\n\n  *   Encender: de L a V (8:30 AM a 19:00 PM)\n  *   Apagar: de L a V deberá estar apagada de 18:59  PM a 8:29 AM (sábados y domingo deberá permanecer apagada)\n\nMV: VFDAZBDZAP02-V2\n\n  *   Encender: de L a V (8:30 AM a 19:00 PM)\n  *   Apagar: de L a V deberá estar apagada de 18:59  PM a 8:29 AM (sábados y domingo deberá permanecer apagada)\n\n\nMV: BCMVDAVD140-0\n\n  *   Encender: de L a V (8:30 AM a 19:00 PM)\n  *   Apagar: de L a V deberá estar apagada de 18:59  PM a 8:29 AM (sábados y domingo deberá permanecer apagada)\n\nQuedo atenta a la atención de esta programación de cambios.\nSaludos Cordiales.\n[Bepensa]\nAlma Valencia Verduzco\n\nGERENCIA DE ATENCIÓN A NEGOCIO\n\n\navalencia@bepensa.com<mailto:>\n\nTel. (33) 3563 8383 Ext. 477\n\nCel. (33) 1455 0383\n\nAv. Circunvalación No.1471 Pisos 4to. y 6to., Col. Lomas del Country,CP:44610 Guadalajara, Jalisco.\n\n\n[Cintillo para apps.jpg]<https://bit.ly/FinBeABCApps>\n\n\n\nEste mensaje es única y exclusivamente para conocimiento del destinatario. El contenido del presente puede ser legal y confidencial, además de contener datos o información recibidos de terceros, por lo que no somos responsables de que sean correctos o completos. Con base al secreto profesional del involucrado, se le solicita por favor que en el caso de recibir este correo por error, lo elimine de manera inmediata. Queda prohibido usar, revelar, divulgar, imprimir o copiar parcial o totalmente este mensaje si no es usted el destinatario. En virtud de que los mensajes electrónicos son altamente manipulables, "Financiera Bepensa S.A de C.V SOFOM ER y/o AB&C Leasing de México S.A.P.I. de C.V. y/o filiales y/o subsidiarias y/o contraloras; no se hacen responsables del material involucrado, del contagio de algún virus informático o mensaje anexo malicioso. Lo anterior de conformidad con el Artículos 210, 211 Bis y 211 Bis 1 al 211 Bis 7 del Código Penal Federal.\n\n	C87AF0DB-319C-432A-8850-29F46FC36402	Requerimiento	0.7041258250457891	2026-03-27 22:55:34.773527	confirmado	t	C87AF0DB-319C-432A-8850-29F46FC36402
f5cc91b8-584e-46f8-ae60-55848feb7675	NO SE PUEDEN VISUALIZAR LAS CARPETAS ELECTRONICAS DE CLIENTES CONAUTO	Buen dia.\nSolicito de su apoyo para poder visualizar las carpetas electronicas de clientes CONAUTO, adjunto imagen	D937532B-6762-4521-9F60-254D2D2D8B2E	Incidente	0.6088551892272265	2026-03-30 15:40:38.803425	corregido	t	C87AF0DB-319C-432A-8850-29F46FC36402
be6d8bf0-cd52-466a-aa58-1db321fd5596	Buenos dias, me saco del Agent Desktop	\N	D937532B-6762-4521-9F60-254D2D2D8B2E	Incidente	0.5856976531927856	2026-03-30 15:40:38.93184	confirmado	t	D937532B-6762-4521-9F60-254D2D2D8B2E
27be29cb-7850-422a-be5a-172b6bbc0823	CONTRATO 1141711	Hola buenos dias, me pueden ayudar de favor con este contrato, al pareser no aparesen los datos de este cliente.\nLA RUTA ES \n-AFIN CON CLAVE INT \n-MODIFICA CONTRATOS	C87AF0DB-319C-432A-8850-29F46FC36402	Requerimiento	0.6672074873245984	2026-05-14 20:22:39.757878	enviado	f	\N
db1e455b-aa22-449d-b51e-602574798270	solicitud de cambio/desbloqueo de contraseña SIR12	Buen día estimado equipo:\n\nPor este medio les envío un cordial saludo y a su vez solicito me ayuden a desbloquear y cambiar el password para mi usuario de SIR12, debido a que lo tengo bloqueado.\nUsuario : MMs987\nBID: 987\nSaludos\nMartha Patricia\nEste mensaje y los datos adjuntos son para uso exclusivo de la persona o entidad a la que expresamente ha sido enviada y puede contener información PRIVILEGIADA y CONFIDENCIAL. Si ha recibido esta comunicación por error: 1) queda estrictamente prohibido la revelación, retransmisión, difusión o el uso de la información contenida, 2) por favor elimine y destruya todas las copias; y 3) favor de informar al remitente. Su cooperación es agradecida. "This message and the attached files are intended only for the use of the addressee and may contain information that is PRIVILEGED and CONFIDENTIAL. If you received this communication in error: 1) disclosure, copying, distribution or taking any action in reliance on the contents of this communication is strictly prohibited; 2) please delete and destroy all copies; and 3) kindly notify us ."Your cooperation is greatly appreciated"\n	C87AF0DB-319C-432A-8850-29F46FC36402	Requerimiento	0.7030001115025516	2026-03-30 15:40:38.93311	confirmado	t	C87AF0DB-319C-432A-8850-29F46FC36402
0a0721ba-08c9-4a7a-a8b0-4d0118767382	RE: Favor de corregir un dato, en contrato 100003546	Muchas gracias,\nYa quedo correcto el formato y firmado por el cliente\nSaludos y excelente fin de semana\nMartha Patricia\n________________________________\nDe: Ventas Especiales <ventasespeciales@conauto.mx>\nEnviado: sábado, 28 de marzo de 2026 14:01\nPara: Martha Patricia Mondragon Soto <mmondragon@changanperinorte.com.mx>; Mesa de Ayuda GConsultores <solicitudes@gconsultores.com.mx>\nCc: Janis Fernanda Rangel Martínez <jrangelm@conauto.mx>; Paola Denisse Crosswell <dcrosswell@conauto.mx>\nAsunto: RE: Favor de corregir un dato, en contrato 100003546\n\n\nBuenas tardes Paty,\n\n\n\nTe anexo la corrección del beneficiario en el seguro de vida.\n\n\n\nSaludos!\n\n\n\n\n\n\n\nVerónica  Carrillo Magallanes\nAnalista Administrativo de Ventas\nTel: 55 5228 7000\n\n[http://52.42.8.189/logocorreo/firma2025.png]\n\n\n\nDe: Martha Patricia Mondragon Soto <mmondragon@changanperinorte.com.mx>\nEnviado el: sábado, 28 de marzo de 2026 12:48 p. m.\nPara: Mesa de Ayuda GConsultores <solicitudes@gconsultores.com.mx>\nCC: Ventas Especiales <ventasespeciales@conauto.mx>\nAsunto: Favor de corregir un dato, en contrato 100003546\n\n\n\nBuenas tardes estimado equipo;\n\nPor este medio solicito corregir un dato apellido materno del Beneficiario del contrato, Debido a que se puso otro y es para el seguro de vida.\n\n\n\nContrato: 100003546/ Marco Antonio del Ángel Pérez\n\n\n\nEl nombre del beneficiario es : Ernesto García Torres\n\nAdjunto imagen de donde se debe cambia: solo apellido materno por "Torres", también les envío la identificación del beneficiario.\n\n[cid:image001.png@01DCBEBB.6A5FD760][cid:image002.png@01DCBEBB.6A5FD760]\n\n[cid:image001.png@01DCBEBB.6A5FD760]\n\nPor favor solo para imprimir el seguro de vida.\n\nSi son tan amables de ayudarme a corregir este dato por favor.\n\nSaludos y excelente día\n\nMartha Patricia Mondragón Soto\n\nEste mensaje y los datos adjuntos son para uso exclusivo de la persona o entidad a la que expresamente ha sido enviada y puede contener información PRIVILEGIADA y CONFIDENCIAL. Si ha recibido esta comunicación por error: 1) queda estrictamente prohibido la revelación, retransmisión, difusión o el uso de la información contenida, 2) por favor elimine y destruya todas las copias; y 3) favor de informar al remitente. Su cooperación es agradecida. “This message and the attached files are intended only for the use of the addressee and may contain information that is PRIVILEGED and CONFIDENTIAL. If you received this communication in error: 1) disclosure, copying, distribution or taking any action in reliance on the contents of this communication is strictly prohibited; 2) please delete and destroy all copies; and 3) kindly notify us .“Your cooperation is greatly appreciated”\n\nEste mensaje y los datos adjuntos son para uso exclusivo de la persona o entidad a la que expresamente ha sido enviada y puede contener información PRIVILEGIADA y CONFIDENCIAL. Si ha recibido esta comunicación por error: 1) queda estrictamente prohibido la revelación, retransmisión, difusión o el uso de la información contenida, 2) por favor elimine y destruya todas las copias; y 3) favor de informar al remitente. Su cooperación es agradecida. “This message and the attached files are intended only for the use of the addressee and may contain information that is PRIVILEGED and CONFIDENTIAL. If you received this communication in error: 1) disclosure, copying, distribution or taking any action in reliance on the contents of this communication is strictly prohibited; 2) please delete and destroy all copies; and 3) kindly notify us .“Your cooperation is greatly appreciated”\nEste mensaje y los datos adjuntos son para uso exclusivo de la persona o entidad a la que expresamente ha sido enviada y puede contener información PRIVILEGIADA y CONFIDENCIAL. Si ha recibido esta comunicación por error: 1) queda estrictamente prohibido la revelación, retransmisión, difusión o el uso de la información contenida, 2) por favor elimine y destruya todas las copias; y 3) favor de informar al remitente. Su cooperación es agradecida. “This message and the attached files are intended only for the use of the addressee and may contain information that is PRIVILEGED and CONFIDENTIAL. If you received this communication in error: 1) disclosure, copying, distribution or taking any action in reliance on the contents of this communication is strictly prohibited; 2) please delete and destroy all copies; and 3) kindly notify us .“Your cooperation is greatly appreciated”\n	C87AF0DB-319C-432A-8850-29F46FC36402	Requerimiento	0.7147406218910796	2026-03-30 15:40:38.67187	confirmado	t	C87AF0DB-319C-432A-8850-29F46FC36402
109dc7c6-48c8-40de-a192-47a2ab73978c	Apoyo en Perfilamiento Expres	Buen día estimados.\n\nCon apoyo en la generación de reporte en Perfilamiento Expres, ya que en la extracción o la generación del reporte en excel no separa los perfilamientos que son de Conauto, GC o Changan. \n\nLos da todos en general sin dividirlos. Solicitamos una columna donde los identifique a cada uno, al generar el reporte y adicional que se coloque el distribuidor.\n\nGracias.	C87AF0DB-319C-432A-8850-29F46FC36402	Requerimiento	0.672806201125858	2026-03-30 22:20:53.735198	confirmado	t	C87AF0DB-319C-432A-8850-29F46FC36402
2e2d1961-2443-41da-a630-5950113e8bad	etiquetas 380  vcr  conauto	Hola buenso dias me ayudan de favor con este caso.Al momento de meter esta etiketa no se guarda.	D937532B-6762-4521-9F60-254D2D2D8B2E	Incidente	0.6924372712185342	2026-05-14 19:50:19.124089	enviado	f	\N
168b875a-7c9e-405e-9033-38a382d5ce4e	3435- 4 / UNIR / No agarra internet la computadora de la becaria	Hola buenos días, solicito su apoyo para venir a revisar la Computadora de Servicios Escolares que no agarra el internet, donde trabaja la becaria de fidelización.\n\nSin más por el momento, quedo al pendiente de su ayuda.\n\nExcelente día.\n\n\n[cid:image001.jpg@01DCE138.3B245FD0]\n  www.universidadriviera.edu.mx<http://www.universidadriviera.edu.mx/>\n\nP Please consider the environment before printing this email.\nAVISO DE PRIVACIDAD\nEste mensaje de correo es confidencial para uso exclusivo y único del destinatario. Queda prohibido el uso, divulgación o distribución de este mensaje sin autorización previa. Si recibió este mensaje por error, por favor avise respondiendo al remitente, elimine este mensaje y destruya cualquier copia. CENTRO EDUCATIVO DE LA RIVIERA A.C. (nombre comercial: UNIVERSIDAD RIVIERA) con domicilio en Av. CTM S/N, Lt 06, Mz-04, entre Av. Flor de ciruelo y Av. Lilis; Colonia Real Ibiza. Solidaridad, Quintana Roo. C.P. 77723, manifiesta que todos los datos personales recabados por medio de este correo electrónico quedan protegidos bajo los lineamientos de nuestro Aviso de Privacidad en cumplimiento con la Ley Federal de Protección de Datos Personales en Posesión de los Particulares. Los datos personales recabados podrán ser utilizados para fines de contacto, para facturación y cobro, para elaborar un expediente académico, para dar seguimiento al aprovechamiento escolar, para asesorías académicas y tutorías, para envío de publicidad. Para conocer mayor información sobre los términos y condiciones en que serán tratados sus datos personales, como los terceros con quienes compartimos su información personal y la forma en que podrá ejercer sus derechos ARCO, puede consultar el Aviso de Privacidad Integral en nuestro sitio:  www.universidadriviera.edu.mx<http://www.universidadriviera.edu.mx/>\n\n\n	C87AF0DB-319C-432A-8850-29F46FC36402	Requerimiento	0.6257375482786736	2026-05-14 19:50:19.19029	enviado	f	\N
f5139ec4-b8f2-488b-a9b4-99cb8fce7c4b	CAPTURA DE CESIÓN DE DERECHOS - PLATAFORMA SIR	Buena tarde.\n\nSolcito de su amable apoyo para poder configurar la plataforma SIR en el apartado de "cesión de derechos", ya que el sistema no permite realizar el cambio de titulares y tenemos 2 casos pendientes que requieren realizar esta operación para mantener clientes con 10 meses de antigüedad.\n\nRuta: SIR>Contratos>BID (823)>Contratos>Captura e impresión de cesión de derechos>Grupo Integrante 5844-017.	D937532B-6762-4521-9F60-254D2D2D8B2E	Incidente	0.4970764196286663	2026-05-14 19:50:19.213428	enviado	f	\N
01f955e2-5af5-4ae7-967f-649423e992a1	REQUERIMIENTO WEB SIR	Buena tarde \n\nSolicitando de su apoyo para que en los reportes arrojados en Web sir se puede visualizar la fecha y hora de captura, así como fecha y hora de respuesta por parte de evaluación así como que en el apartado de aufinanciamiento se actualice la fecha una ves que reingresa ya que se queda con la fecha de captura y no aparece el dia que reingreso\n\nQuedo atento \n\nSaludos	C87AF0DB-319C-432A-8850-29F46FC36402	Requerimiento	0.5654672376996935	2026-05-14 19:50:19.188876	enviado	f	\N
cbf7ee15-d713-4d55-ab21-8a7496d926b7	4407 / Grupo Ordoñez / Sin Acceso a SAP / Actividades Gloria Medina	Buen día.\n\nSe genera ticket para el registro de actividades de Gloria Medina, por el tema del incidente de Microsoft que hubo el día 24 de Abril que afecto al cliente Ordoñez	C87AF0DB-319C-432A-8850-29F46FC36402	Requerimiento	0.4688854059789055	2026-05-14 19:50:19.239605	enviado	f	\N
37b742f8-7afa-401f-9cc0-323761906190	3435-4 / UNIR / Solicitud de Licenciaturas Online	Buenas tardes César,\n\nTe comento, el alumno David Yllescas Valdez me comparte que no puede acceder a su sesión en Microsoft debido a que le notifica que la licencia no es valida.\n¿Me podrías asesorar respecto a que significa y que acciones podemos tomar?\n\n[cid:2a9ffe1b-fe88-48e9-8a0c-123140f846d9]\n\nSaludos\n\n[cid:83982236-3f08-4ffc-8072-3d2d5cf3308c]\n	C87AF0DB-319C-432A-8850-29F46FC36402	Requerimiento	0.7127427369834214	2026-05-14 19:50:18.932358	enviado	f	\N
59aa8f11-8533-4f70-a436-5448ff81e7fa	SELECCION DE VENDEDOR GC	Buen día,\n\nSolicito su apoyo ya que al querer seleccionar vendedor a un crédito de GC, no me sale ninguno y dicho vendedor ya está dado de alta y ligado al BID correspondiente.\n\nPor favor apóyenme, ya que si no selecciono vendedor no me deja continuar el proceso y no me genera el número de folio en 8000...	D937532B-6762-4521-9F60-254D2D2D8B2E	Incidente	0.674931510772556	2026-05-14 19:50:19.009104	enviado	f	\N
90179fe7-ef26-4ea8-a9d6-6ad0934d7a8c	Mesa Cero - Impresora con atasco de papel	El equipo se apaga solo a los pocos minutos de encenderse. Impacto detectado: Riesgo de pérdida de datos por fallos de disco. Acciones previas realizadas: El usuario confirma que el incidente ocurre desde ayer. Se solicita intervención del equipo de soporte para resolución.	D937532B-6762-4521-9F60-254D2D2D8B2E	Incidente	0.6913664880543687	2026-05-16 00:48:17.246195	confirmado	f	D937532B-6762-4521-9F60-254D2D2D8B2E
859e45dd-effd-4b57-8052-c6969dc805ab	Ayuda con portal Conauto	Buenos días \n\nPor favor me pueden apoyar con el web sir en conauto, no me permite ingresar. Gracias	D937532B-6762-4521-9F60-254D2D2D8B2E	Incidente	0.6816826060742349	2026-05-25 23:04:40.035235	pendiente	f	\N
34ca3430-9007-4d9f-89c5-0511ed08146a	GCTI / invitación a grupo externo	Hola buen día\nMe llego la invitación para un grupo externo:\nDespués de lo sucedido con Memo, no he aceptado ni nada\n[cid:image001.png@01DCE9F9.E9CB1000]\nC.P. ANA CECILIA MEDINA KU\nCONTADOR\nGrupo Consultores en Tecnología Informática\nAv Andrés García Lavín Esq. Con 43 Y 41  Num 337-B Planta alta\nMérida, Yucatán. C.P. 97117\nTel.  (999) 941.87.88 ext  116\nLADA sin costo: 01.800.700.4242\n\nwww.gconsultores.com.mx\n\n	D937532B-6762-4521-9F60-254D2D2D8B2E	Incidente	0.5564748213095152	2026-05-25 23:04:40.627068	pendiente	f	\N
fff23d11-64aa-48eb-bf92-f5d4d062661e	3472 / Enkontrol / MV -ENKV-MARKETPLAC	Se detecto que el recurso (ENKV-MARKETPLAC)  tiene el disco C:\\ con\n20% de capacidad	D937532B-6762-4521-9F60-254D2D2D8B2E	Incidente	0.646307239918002	2026-03-31 19:20:55.129277	confirmado	f	D937532B-6762-4521-9F60-254D2D2D8B2E
d1059281-63b5-43fe-b172-95d7a682abfb	3435-4 / UNIR / Reseteo autentificacion Muiltifactor	De: Gabriela Calderon <gabriela.calderon@universidadriviera.mx>\nEnviado: Jueves, 26 de Marzo de 2026 19:02\nPara: Cesar Zamora Hernández <cesarz@gconsultores.com.mx>\nCC: Dulce Montemayor <dulce.montemayor@universidadriviera.mx>\nAsunto: RV: Falla en cuenta Microsoft \n\nBuenas tardes Cesar\nMe apoyas dando seguimiento a la petición de la estudiante por favor.  De: Citlali Jamin Delgado Gil <AU225687@universidadriviera.mx>\nEnviado el: martes, 24 de marzo de 2026 07:30 p. m.\nPara: Cesar Zamora Hernández <cesarz@gconsultores.com.mx>\nCC: Gabriela Calderon <gabriela.calderon@universidadriviera.mx>; David israel Becerra Martin <david.becerra@universidadriviera.mx>\nAsunto: Falla en cuenta Microsoft Buenas Tardes, estimado Ing. César Zamora Por este medio me presento, soy Citlali Delgado, de la Licenciatura de Psicología, en la Universidad Riviera. Envíe hace unas semanas un correo notificando un problema en mi cuenta Microsoft de la escuela. Tengo un detalle para abrir mi cuenta de Microsoft debido a una falla en la aplicación de Authenticator, por lo que no puedo acceder a mi cuenta de M365, mi cuenta de Word, Excel y PowerPoint, registradas a este correo, a mi correo Outlook en mi iPad, one drive, Teams. No sé qué solución le podríamos dar a esta situación, sé que no es directamente de la universidad el problema, si no del proveedor de servicio (Microsoft). Sin embargo, no sé si exista otra manera para que yo acceda a la información, pues ahora me es necesaria para un diplomado que estoy tomando, así como documentación importante.   También lo que sucede es que cambié de número telefónico, y eso está relacionado, los códigos de verificación no me llegan a la app de Authenticator, y como cambié de número no puedo hacer que me lleguen al número, he tratado de cambiar mi número en la app, pero cada la aplicación abro no me permite acceder para cambiar el número.  Si de algo sirve le dejo mi número anterior 984 186 03 54 y ahora es 999 551 0966.   Muchas gracias de antemano.    Obtener Outlook para iOS	D937532B-6762-4521-9F60-254D2D2D8B2E	Incidente	0.4962308285076536	2026-03-27 21:40:47.901823	confirmado	t	D937532B-6762-4521-9F60-254D2D2D8B2E
a5a1c4fb-a717-45e6-a464-66224a98ed02	Favor de corregir un dato, en contrato 100003546	Buenas tardes estimado equipo;\nPor este medio solicito corregir un dato apellido materno del Beneficiario del contrato, Debido a que se puso otro y es para el seguro de vida.\n\nContrato: 100003546/ Marco Antonio del Ángel Pérez\n\nEl nombre del beneficiario es : Ernesto García Torres\nAdjunto imagen de donde se debe cambia: solo apellido materno por "Torres", también les envío la identificación del beneficiario.\n[cid:a9d53cec-031f-4e86-9d8d-91ff39c3eca1][cid:a0d5670d-64df-4fb5-a736-e1f35fc3696c]\n[cid:063d30b6-baa5-420b-98fa-03997a6336b4]\nPor favor solo para imprimir el seguro de vida.\nSi son tan amables de ayudarme a corregir este dato por favor.\nSaludos y excelente día\nMartha Patricia Mondragón Soto\nEste mensaje y los datos adjuntos son para uso exclusivo de la persona o entidad a la que expresamente ha sido enviada y puede contener información PRIVILEGIADA y CONFIDENCIAL. Si ha recibido esta comunicación por error: 1) queda estrictamente prohibido la revelación, retransmisión, difusión o el uso de la información contenida, 2) por favor elimine y destruya todas las copias; y 3) favor de informar al remitente. Su cooperación es agradecida. "This message and the attached files are intended only for the use of the addressee and may contain information that is PRIVILEGED and CONFIDENTIAL. If you received this communication in error: 1) disclosure, copying, distribution or taking any action in reliance on the contents of this communication is strictly prohibited; 2) please delete and destroy all copies; and 3) kindly notify us ."Your cooperation is greatly appreciated"\n	C87AF0DB-319C-432A-8850-29F46FC36402	Requerimiento	0.729026717231301	2026-03-30 15:40:38.869271	confirmado	t	C87AF0DB-319C-432A-8850-29F46FC36402
660b5a77-deca-4176-9869-bce87be9daec	NO TIENE DESCRIPCION DE LA UNIDAD CTO 100003551	Buenas tardes\n\nSolicito su apoyo, ya que en el estado de cuenta 100003551 de GC Conautopción no viene la descripción de la unidad, la cual es: TH2 TERRITORY TREND HEV, adjunto imágen.\n\n\n\nAgradeciendo de antemano su atención y apoyo a la presente.\n\nAtte.\nMaría del Carmen Ríos Fierro.\nAnalista de Operaciones	C87AF0DB-319C-432A-8850-29F46FC36402	Requerimiento	0.6300710443607337	2026-03-31 00:20:38.508516	confirmado	f	C87AF0DB-319C-432A-8850-29F46FC36402
9b071f92-2891-4f5d-8f1f-a5c38d789fd0	PV + 4744 / Bazar del Dulcero / Nube para SAP CRM:0023090	Hola Herberth Novelo ,\n\nPor este medio te solicito de favor me ayudes con la generación de una propuesta técnica para la oportunidad 4744 Bazar Nube para SAP .\n\nLa fecha compromiso es 06/04/2026 12:00 a. m. \n\nAgradeciendo de antemano la atención y apoyo, quedo a tus órdenes.\n\nAtte.\n\n Roger Guevara Gonzalez \n	C87AF0DB-319C-432A-8850-29F46FC36402	Requerimiento	0.5032072080908454	2026-03-31 18:20:55.309563	confirmado	f	C87AF0DB-319C-432A-8850-29F46FC36402
6fd389ce-7fed-4bde-8659-bf858bc4bd84	CAMBIO DE EQUIPO DE COMPUTO	Buen dia\n\nSolicito de su amable apoyo para el cambio de mi equipo de cómputo ya que algunas teclas no funcionan, se apaga el equipo y la bateria no dura (30 aprox) en uso no conectada\n\nSin mas por le momento, agradezco su ayuda\n\nSaludos	C87AF0DB-319C-432A-8850-29F46FC36402	Requerimiento	0.6482999404586992	2026-05-25 23:04:40.262595	pendiente	f	\N
15cd7f9f-1129-47ff-8470-eb8edbd42975	CANCELACION DE SEGUROS POR JUICIO	Buen dia\nme pueden apoyar en AFIN12 no me deja cancelar el seguro automotriz por juicio me sale este aviso , me pueden apoyar por favor\n\n\nagradezco su apoyo\nsaludos.	C87AF0DB-319C-432A-8850-29F46FC36402	Requerimiento	0.6883151880223273	2026-04-01 20:00:57.784682	confirmado	f	C87AF0DB-319C-432A-8850-29F46FC36402
07e986cc-87d9-4813-9f41-ceaf7d7faa27	Nuevo requerimiento de propuesta técnica 4745 Ordoñez PETI CRM:0023091	Hola Manuel Alcocer ,\n\nPor este medio te solicito de favor me ayudes con la generación de una propuesta técnica para la oportunidad 4745 Ordoñez PETI .\n\nLa fecha compromiso es 06/04/2026 12:00 a. m. \n\nAgradeciendo de antemano la atención y apoyo, quedo a tus órdenes.\n\nAtte.\n\n Roger Guevara Gonzalez \n	C87AF0DB-319C-432A-8850-29F46FC36402	Requerimiento	0.4951128737644416	2026-03-31 18:20:55.173577	enviado	f	\N
5db0fa9c-b89e-4285-8021-702d5b2cc9ec	3720-7 / Compañía Fernandez / Acceso a servidor de pilot	La persona que me apoya en el desarrollo de la herramienta pilot, entraba al server via escritorio remoto usando la siguiente url: pilot.fernandez.com.mx:19856 y desde hace como un mes no puede entrar, pueden validar por favor	C87AF0DB-319C-432A-8850-29F46FC36402	Requerimiento	0.5385017591391493	2026-05-14 19:50:19.051102	enviado	f	\N
3f1b3156-2ad9-49aa-b6b5-f302e701f16b	SIN VISUALIZAR EL BOTON DE PERFILAMIENTO WEB SIR	ME PUEDEN APOYAR YA QUE EN EL WEB SIR NO SE VISUALIZAR  EL BOTON DE PERFILAMIENTO EN EL WEB SIR CON EL USUARIO alopezg con perfil de operaciones	D937532B-6762-4521-9F60-254D2D2D8B2E	Incidente	0.6448331882406755	2026-05-25 23:04:43.175835	pendiente	f	\N
d50218d2-0b09-437f-be7b-f2bb3e83ef8d	3472 / Enkontrol / Tareas Programadas Windows. PRIORITARIO	Anexo documento de PROBLEMATICA que se nos ha presentado con las tareas de windows\nEn el documento viene el detalle.\nRequierimos por favor alguna alternativa de solución a este problema. Ya nos ha generado varias quejas de los clientes	D937532B-6762-4521-9F60-254D2D2D8B2E	Incidente	0.551755732593786	2026-05-14 19:50:18.938499	enviado	f	\N
a316fea1-5794-42b0-83ed-59e07929b6a8	Pase a QA y Producción Conauto	\N	OTROS	Otros	0.5394343561875874	2026-05-25 23:04:43.355787	pendiente	f	\N
404ef077-b137-49e0-840c-349dcdb0cfe7	CESION DE DERECHOS 5839-013	ME APOYAN A QUE SE GUARDE LA CESION DE DERECHOS YA QUE NO ME PERMITE CAMBIAR AL NUEVO TITULAR \nAFIN//CESION DE DERECHOS//	C87AF0DB-319C-432A-8850-29F46FC36402	Requerimiento	0.5389980425471594	2026-05-25 23:04:43.559388	pendiente	f	\N
69b0950f-28ee-4243-ad15-f1e4fc206737	Cambio de contraseña	No me dejó hacer el cambio de contraseña me mandó directamente con el servicio técnico.\nAUIRRB\nPrueba1	C87AF0DB-319C-432A-8850-29F46FC36402	Requerimiento	0.6463066824759659	2026-05-25 23:04:40.328717	pendiente	f	\N
e518134a-621c-47b6-a3c9-8ac98bad6871	ERROR AL VALIDAR USUARIOY PASSWORD ADJMRF EN CONAUTOPCION SOFOM	Buen día, \n\nSolicito su apoyo, no puedo accesar al progress en Conautopción en SOFOM, al parecer ya se vencio mi password es en ADJMRF.\n\n\n\nAgradeciendo de antemano su atención y apoyo a la presente.\n\nAtte.\nMaría del Carmen Ríos Fierro.\nAnalista de Operaciones	D937532B-6762-4521-9F60-254D2D2D8B2E	Incidente	0.540640632432506	2026-04-06 16:40:52.392777	enviado	f	\N
1627ef26-45ba-4c92-9e24-91d8f66d1205	SOLICITUD DE TICKETS	Buenos días. Si me pudiesen apoyar con la siguiente solicitud de ticket.\n\nCampo\nDato requerido\nTitulo del ticket\nSeguimiento a errores de Veeam Cloud\nDescripción del ticket\nSeguimiento a errores recurrentes en Veeam Cloud Connect\nNombre del usuario (Cliente) que se le cargará el ticket\nHerberthn@gconsultores.com.mx<mailto:Herberthn@gconsultores.com.mx>\nTipo de solicitud (seleccionar opción de la lista)\nRequerimiento\nFecha de finalización del ticket\n30/4/2026\nTipo de servicio (seleccionar opción de la lista)\nSin cobro\nIngeniero asignado al ticket\nericko@gconsultores.com.mx<mailto:ericko@gconsultores.com.mx>\n\n	C87AF0DB-319C-432A-8850-29F46FC36402	Requerimiento	0.7303706176665177	2026-04-06 17:00:54.242613	enviado	f	\N
523cc5b6-dd6c-444a-8255-2c12e9422212	ENVIO EDO CUENTA CONAUTO	Por este medio solicito apoyo, al momento de generar un estado de cuenta de conauto para envio a Titular se genera sin información, apareciendo el siguiente error:	D937532B-6762-4521-9F60-254D2D2D8B2E	Incidente	0.5026804160636529	2026-04-06 17:20:52.590587	enviado	f	\N
11c2f4ff-bb7f-4085-a2e5-74286f66ba1a	3534-4 / UNIR / Problemas WIFI  Aula 5	De: Citlally Hernández Castro <citlally.hernandez@universidadriviera.mx>\nEnviado: Lunes, 06 de Abril de 2026 12:17\nPara: Cesar Zamora Hernández <cesarz@gconsultores.com.mx>\nAsunto: Problemas con la red \n\nBuena tarde Mtro. \nEl día de hoy, los alumnos del Mtro. Raúl Venancio nos reportan fallas con el internet, nos pueden apoyar con revisar la situación. \nGracias.	D937532B-6762-4521-9F60-254D2D2D8B2E	Incidente	0.6651689819736382	2026-04-06 17:40:52.315801	enviado	f	\N
7aff45c3-bc20-4a17-b2f5-a059aab1e9d3	REQ. 2026-001825	Buen día.\n\nDisculpen no tengo respuesta del ticket y necesito verificar datos en Progress SOFOM con ADJMRF con mi password ya no puedo entrar sale la siguiente imagen de que HA EXCEDIDO EL NUMERO DE INTESTOS PARA INGRESAR AL SISTEMA.\n\nSolicito su apoyo.\n\nAtte.\nMaría del Carmen Ríos Fierro\nAnalista de Operaciones	D937532B-6762-4521-9F60-254D2D2D8B2E	Incidente	0.6417289742252983	2026-04-06 18:00:52.46777	enviado	f	\N
e7f1f708-dcd6-4d53-9c10-f21ca127b789	3472 / Enkontrol / Seguimiento a errores de Veeam Cloud	Seguimiento\na errores recurrentes en Veeam Cloud Connect	C87AF0DB-319C-432A-8850-29F46FC36402	Requerimiento	0.4490250047177908	2026-04-06 21:40:52.125899	enviado	f	\N
cbeeb79a-9430-4be3-a939-32d9364163df	no me permite guardar PDF	Hola buen dia!\n\nDe su apoyo para darme acceso a poner guardar archivos en PDF	D937532B-6762-4521-9F60-254D2D2D8B2E	Incidente	0.6429234104424227	2026-05-25 23:04:40.782374	pendiente	f	\N
3d603c27-b10f-43f7-93c2-1051e37efd0e	5755-007 FACTURA	Hola buenos días me pueden ayudar de favor a visualizar las imagenes	C87AF0DB-319C-432A-8850-29F46FC36402	Requerimiento	0.4997004980622508	2026-05-25 23:04:42.834998	pendiente	f	\N
a3db3a4e-bb1f-4ec2-946f-ffc38d37f20a	BOTON PERFILAMIENTO WEBSIR	Buenas tardes,\n\nMe apoyan por favor, ya que de acuerdo al proceso después de consultar el buró de un cliente, da la opción de "PERFILAMIENTO" pero no me aparece el botón, anexo imágen.\n\n\n\n\n\n\n\nQuedo atenta.\n\nSaludos!	D937532B-6762-4521-9F60-254D2D2D8B2E	Incidente	0.5139433219844299	2026-05-25 23:04:43.293041	pendiente	f	\N
b6d5686c-0fff-4d4b-af35-8cd10e29a117	GRUPO INTEGRANTE 8487-015	Hola buenos días, me pueden ayudar de favor con este grupo integrante, cuando lo acepta digitalmente en el SIR no me da otro grupo integrante.\n\n\n \n\nLA RUTA ES:\nMENU GENERAL CON CLAVE INT \nCONTROL VALIJA\nRECEPCION\nCONTROL VALIJA	C87AF0DB-319C-432A-8850-29F46FC36402	Requerimiento	0.5140924835635664	2026-04-20 16:38:44.850285	enviado	f	\N
6b988fd1-414a-4570-856a-21aead197d1e	Seguimiento a REQ 2026-002422	Buenos dias.\n\nLes pido por favor saber el status de este tiket REQ 2026-002422, ya que al dia de hoy no tenemos respuesta.Gracias.	C87AF0DB-319C-432A-8850-29F46FC36402	Requerimiento	0.6342021232875159	2026-05-25 23:04:43.350869	pendiente	f	\N
e737f089-09b8-4373-b3d7-82af6d500b8c	DIGITALIZACION DE FACTURA 5808-42	ME PODRIAN APOYAR CON LA DIGITALIZACION DE LA FACTURA, ESTA NO SE ENCUENTRA EN EL SISTEMA \nsALUDOS	C87AF0DB-319C-432A-8850-29F46FC36402	Requerimiento	0.7107446945914296	2026-04-28 17:18:01.658837	enviado	f	\N
f2d42ef7-ee38-44d6-8eff-80bf5d33bf64	Favor de apoyar con solicitud	Campo\nDato requerido\nTitulo del ticket\n4354-1 Fernández Baas -Revision Warnings\nDescripción del ticket\nSe detecto warnings en diferentes Jobs del cliente Fernandez"Task failed. Error: RPC deadline: 05.04.2026 13:31:38.333 UTC for invocation of LockService.LockGroups has been exceeded" favor de revisar\nNombre del usuario (Cliente) que se le cargará el ticket\nAlfredo Canche\nTipo de solicitud (seleccionar opción de la lista)\nIncidente\nFecha de finalización del ticket\n07/04/2026\nTipo de servicio (seleccionar opción de la lista)\nProyecto\nIngeniero asignado al ticket\nericko@gconsultores.com.mx<mailto:ericko@gconsultores.com.mx>\n\n	D937532B-6762-4521-9F60-254D2D2D8B2E	Incidente	0.4955316369315787	2026-04-06 16:40:52.391306	enviado	f	\N
a984b42e-64da-4275-bfc4-64effcf18e21	GRUPO INTEGRANTE 8487-020	Hola buenos días, me pueden ayudar de favor con la aceptacion digital, no me da otro grupo integrante.\n\n\nLA RUTA ES \nMENU GENERAL CON CLAVE INT \nCONTROL VALIJA \nRECEPCION\nCONTROL VALIJA	C87AF0DB-319C-432A-8850-29F46FC36402	Requerimiento	0.5356317634582728	2026-04-20 18:48:43.647872	corregido	f	C87AF0DB-319C-432A-8850-29F46FC36402
9222f1a1-f35a-408f-a901-b16826481536	FALLA EN REPORTE DE VENTAS GC CONAUTOPCIÓN	\N	D937532B-6762-4521-9F60-254D2D2D8B2E	Incidente	0.5544176682204436	2026-05-25 23:04:43.471556	pendiente	f	\N
32fbd7e2-5b37-4368-8c92-efa5928a22b7	simulador GC CONAUTOPCION  para aplicar reduccion de mensualidad	Buenas tardes cesar\nAyúdame por favor con este cambio que hicieron movieron la tabla de simulación para cuando los clientes hacen el pago , el cliente pago 100,000 pesos para reducir su mensualidad pero el sistema lo emitió mal  sistema emitió una mensualidad de $18,060.46, cuando lo correcto debió ser $24,656.59, en el estado de cta interno si aparece así , pero la tabla de simulación no esta correcta por que da 18,060.46, al parecer no esta respetando el seg de vida y el seg automotriz  RUTA - SOFOM MENU GENERAL -V12 / MAS OPCIONES /NUEVO SIMULADOR .   \n\nQuedo al pendiente \n\nadjunto ruta	C87AF0DB-319C-432A-8850-29F46FC36402	Requerimiento	0.6746491526729086	2026-05-14 19:50:19.083537	enviado	f	\N
7f15ad69-7ebd-47b8-9c13-23ff78206076	MULTITAREAS	Hola buenos días me ayudan de favor a poder abrir todo a la vez el menú general, el afín y etc.	C87AF0DB-319C-432A-8850-29F46FC36402	Requerimiento	0.6005406851108407	2026-05-14 19:50:18.963283	enviado	f	\N
f1bb85bb-f1fe-413a-8b62-1efdedd17cee	4354-2 / Compañía Fernandez / Baas / Revision Warnings	Se detecto warnings en diferentes Jobs del cliente Fernandez "Unable to process the workload: your license has been exceeded" favor de revisar	D937532B-6762-4521-9F60-254D2D2D8B2E	Incidente	0.6449850713945628	2026-04-01 20:00:57.867607	enviado	f	\N
94737b57-0332-4273-9bb6-4c338fbe8445	ACTUALIZACION DE SISTEMA	De: Esther Cabrera [mailto:gcia.ventas@fordtlaxcala.com.mx]\n\n\nEnviado el: miércoles, 1 de abril de 2026 12:29 p. m.\n\nPara: 'Ángel David Maqueda Cruz' <amaquedac@conauto.mx>; 'Dulce Belén\nRomero Álvarez' <dromeroa@conauto.mx>;\n'Mesa de Servicios de TI' <Solicitudes@gconsultores.com.mx>\n\nCC: 'Miguel Angel Olvera Andrade' <molveraa@conauto.mx>\n\nAsunto: RE: ACTUALIZACION DE SISTEMA \n\n \n\nHola David buen día, gusto en\nsaludarte. \n\n \n\nSerá que me puedas apoyar, aun no\npuedo generar pdf en ESOF12 me aparece este error. Lo reporte aquí con mi área\nde sistemas y me comenta que el sistema busca un archivo que no tengo instalado\npara poder generarla. \n\n \n\nQuedo atenta a sus comentarios .\n\n\n\n\n\n \n\n\n\n\n\nMa. Esther Cabrera\n\nGerencia Ventas\n\nRivera Tlaxcala\n\nCarretera Federal Mex.-Ver Km 114+450 N°. 137\n\nSanta Úrsula Zimatepec, Yauhquemehcan, Tlaxcala.\n\nCP 90450\n\nTel: 241 689 0500 ext. 8300\n\ngcia.ventas@fordtlaxcala.com.mx\n\n\n\n De: Esther Cabrera [mailto:gcia.ventas@fordtlaxcala.com.mx]\n\n\nEnviado el: miércoles, 1 de abril de 2026 12:29 p. m.\n\nPara: 'Ángel David Maqueda Cruz' <amaquedac@conauto.mx>; 'Dulce Belén\nRomero Álvarez' <dromeroa@conauto.mx>;\n'Mesa de Servicios de TI' <Solicitudes@gconsultores.com.mx>\n\nCC: 'Miguel Angel Olvera Andrade' <molveraa@conauto.mx>\n\nAsunto: RE: ACTUALIZACION DE SISTEMA \n\n \n\nHola David buen día, gusto en\nsaludarte. \n\n \n\nSerá que me puedas apoyar, aun no\npuedo generar pdf en ESOF12 me aparece este error. Lo reporte aquí con mi área\nde sistemas y me comenta que el sistema busca un archivo que no tengo instalado\npara poder generarla. \n\n \n\nQuedo atenta a sus comentarios .\n\n\n\n\n\n \n\n\n\n\n\nMa. Esther Cabrera\n\nGerencia Ventas\n\nRivera Tlaxcala\n\nCarretera Federal Mex.-Ver Km 114+450 N°. 137\n\nSanta Úrsula Zimatepec, Yauhquemehcan, Tlaxcala.\n\nCP 90450\n\nTel: 241 689 0500 ext. 8300\n\ngcia.ventas@fordtlaxcala.com.mx	C87AF0DB-319C-432A-8850-29F46FC36402	Requerimiento	0.5143145441145933	2026-04-01 23:00:57.246733	enviado	f	\N
47413243-69d0-48eb-889b-fc39aef4c839	WEB SIRR CHANGAN	Hola buenos dias me pueden ayudar de favor a que pueda entrar al web sirr changan, se queda congelado y no avanza.	D937532B-6762-4521-9F60-254D2D2D8B2E	Incidente	0.527763301358972	2026-05-14 19:50:18.118672	enviado	f	\N
13956697-ac09-450c-96ea-9644d8ecffe3	4431-2 / BE GRAND / Plataforma no disponible	No se tiene alcance a los servidores de azure por la VPN que apunta hacia el sitio, se valido ip locales de VPN de SAnta FE esas estan ok, las de azure no responden favor de validar	D937532B-6762-4521-9F60-254D2D2D8B2E	Incidente	0.7415323530268423	2026-05-14 19:50:18.68045	enviado	f	\N
4e53a76b-4034-45b2-ac69-ffb5cc1f92ba	RESTABLECER CONTRASEÑA PROGRESS  Y ERROR CAMBIO CONTRASEÑA PROGRESS FINANCIERA	Buenas tardes,-Solicito se restablezca mi contraseña de mi usuario TESFIS en progress SOFOM  ya que caduco\n-Solicito que revisen porque no puedo cambiar la contraseña en QA el sistema me manda el siguiente error:Gracias por su amable atencion,	C87AF0DB-319C-432A-8850-29F46FC36402	Requerimiento	0.6569929305765395	2026-05-14 19:50:18.735736	enviado	f	\N
d73b6e42-955e-43cf-9a60-5799c259a461	PRUEBA	HHWEHWD	C87AF0DB-319C-432A-8850-29F46FC36402	Requerimiento	0.7043884023114575	2026-05-25 23:04:40.409296	pendiente	f	\N
cb5804f7-f987-4f89-88b2-e53aa776d82d	ERROR EN SISTEMA AFIN / ETIQUETA CLIENTE FALLECIDO 5822-017 VALENCIA XICOTENCATL JOSE LUIS	Buenos días. \n\nFavor de revisar el correcto funcionamiento del sistema al utilizar la opción Etiqueta cliente fallecido; al aplicar el siniestro el sistema no realiza movimientos al estado e cuenta interno; ruta : afin<operacion<etiqueta cliente fallecido<gpo-int<consultar= ERROR	C87AF0DB-319C-432A-8850-29F46FC36402	Requerimiento	0.7378696120505382	2026-05-14 19:50:18.7833	enviado	f	\N
4816ce58-c553-4d6c-965b-be8139329337	Internet Lento en Oficina	Favor de validar el wifi de la oficina, ya que se encuentra lento e intermitente	D937532B-6762-4521-9F60-254D2D2D8B2E	Incidente	0.678823208956847	2026-05-08 00:10:08.740536	confirmado	f	D937532B-6762-4521-9F60-254D2D2D8B2E
18919535-3d1d-48be-bc49-9e4208cdc073	Proyecto Interno / Replicar las clasificaciones de las oportunidades de los proyectos a Proactivanet (Fatima)	Buen día\n\nSe genera ticket para el registro de actividades de Fatima Cante para el proyecto interno de Replicar las clasificaciones de las oportunidades de los proyectos a Proactivanet	C87AF0DB-319C-432A-8850-29F46FC36402	Requerimiento	0.48901826793166625	2026-05-25 23:04:40.577344	pendiente	f	\N
cfd96df0-a8e1-49b8-8b52-eedff8a497c0	PV + 4285-2 / Hogares y Promociones / Azure 2026 CRM:0045900	Hola herberth,\n\n\n\nPor este medio te solicito de favor me ayudes con la generacion de una propuesta técnica para la oportunidad 4285-2 RNV Hogares Azure 2026 .\n\n\n\nEsta oportunidad -2 se ocupa propiamente para la renovacion del periodo del 2026 al 2027 de manera administrativa y comercial. Sin embargo podemos incluir lo que el cliente desee incrementar, salvo comentarios tecnicos.\n\n\n\n\n\n¿Me puedes apoyar con una cotización de almacenamiento en la nube de 10 TB para respaldar la información del servidor actual de Éxito PowerEdge T340, por favor?  Estuve revisando el tema con el Ing. Herberth y posiblemente la solución sea mediante Azure Files, ya que necesitamos conservar los permisos NTFS / ACLs de las carpetas compartidas.\n\n\n\nLa fecha compromiso es 22/05/2025  4pm\n\n\n\nAgradeciendo de antemano la atención y apoyo, quedo a tus órdenes.\n\nAtte.\n\n\n\n​[cid:image.jpeg@50747e09c904a5008b4d4ba.50747e09c]<www.gconsultores.com.mx>\n	C87AF0DB-319C-432A-8850-29F46FC36402	Requerimiento	0.7063267672524872	2026-05-25 23:04:43.35749	pendiente	f	\N
2d7a713e-e347-49c3-ae76-5dc7b1940697	GCTI /  Server de Nomina: vm-eus-srvdbsnom	Se detecto que el server de nomina vm-eus-srvdbsnom tiene una alerta de\nespacio "Almacenamiento en C: de 19.2 %"	C87AF0DB-319C-432A-8850-29F46FC36402	Requerimiento	0.4607305091489607	2026-05-14 19:50:18.784755	enviado	f	\N
d4eccb3c-37fa-41f6-a832-9740072089f9	4637 / Petromayab / Acompañamiento Contabilidad Electronica	Buen día.\n\nSe levanta ticket para el registro de actividades de Guillermo Orozco para el acompañamiento de la configuración de Contabilidad Electronica para el cliente Petromayab	C87AF0DB-319C-432A-8850-29F46FC36402	Requerimiento	0.7362512667006487	2026-05-25 23:04:43.557054	pendiente	f	\N
067ad6bb-f18d-4149-b4de-c175ceeca482	4249-1 / TELERED / Campos de tasa de descuento deben mostrarse con 2 decimales en el Front End	Buenas tardes. \nSolicito que en el Front End todos los campos de tasa de descuento se muestren a dos decimales. Ejemplo, el campo tasa actual de descuento en la plantilla de cambio de tasa de descuento.	C87AF0DB-319C-432A-8850-29F46FC36402	Requerimiento	0.6605567169383985	2026-05-25 23:04:43.589766	pendiente	f	\N
\.


--
-- TOC entry 3443 (class 0 OID 0)
-- Dependencies: 215
-- Name: api_users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: ml_user
--

SELECT pg_catalog.setval('public.api_users_id_seq', 1, true);


--
-- TOC entry 3444 (class 0 OID 0)
-- Dependencies: 217
-- Name: models_id_seq; Type: SEQUENCE SET; Schema: public; Owner: ml_user
--

SELECT pg_catalog.setval('public.models_id_seq', 12, true);


--
-- TOC entry 3281 (class 2606 OID 34580)
-- Name: api_users api_users_pkey; Type: CONSTRAINT; Schema: public; Owner: ml_user
--

ALTER TABLE ONLY public.api_users
    ADD CONSTRAINT api_users_pkey PRIMARY KEY (id);


--
-- TOC entry 3283 (class 2606 OID 34582)
-- Name: api_users api_users_username_key; Type: CONSTRAINT; Schema: public; Owner: ml_user
--

ALTER TABLE ONLY public.api_users
    ADD CONSTRAINT api_users_username_key UNIQUE (username);


--
-- TOC entry 3285 (class 2606 OID 34941)
-- Name: models models_pkey; Type: CONSTRAINT; Schema: public; Owner: ml_user
--

ALTER TABLE ONLY public.models
    ADD CONSTRAINT models_pkey PRIMARY KEY (id);


--
-- TOC entry 3279 (class 2606 OID 26289)
-- Name: tickets_feedback tickets_feedback_pkey; Type: CONSTRAINT; Schema: public; Owner: ml_user
--

ALTER TABLE ONLY public.tickets_feedback
    ADD CONSTRAINT tickets_feedback_pkey PRIMARY KEY (id);


--
-- TOC entry 3288 (class 2606 OID 35102)
-- Name: models unique_model_file; Type: CONSTRAINT; Schema: public; Owner: ml_user
--

ALTER TABLE ONLY public.models
    ADD CONSTRAINT unique_model_file UNIQUE (archivo);


--
-- TOC entry 3286 (class 1259 OID 35010)
-- Name: unico_modelo_activo; Type: INDEX; Schema: public; Owner: ml_user
--

CREATE UNIQUE INDEX unico_modelo_activo ON public.models USING btree (activo) WHERE (activo = true);


-- Completed on 2026-06-09 12:58:49

--
-- PostgreSQL database dump complete
--

\unrestrict DesEX0Vb8aTQkVnBxHPuU0DthzfeK4eK5XKz6ZYLI4ORUszHxzvwHqlXZ3AEeYo

