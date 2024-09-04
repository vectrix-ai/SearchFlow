class Prompts:
   
   sql_agent_prompt = """Given an input question, first create a syntactically correct {dialect} query to run, then look at the results of the query and return the answer.
Use the following format:

Question: "Question here"
SQLQuery: "SQL Query to run"
SQLResult: "Result of the SQLQuery"
Answer: "Final answer here."

Only use the following table:
DDL:
CREATE TABLE document_metadata (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    author VARCHAR(255),
    file_type VARCHAR(50),
    word_count INTEGER,
    language VARCHAR(50),
    source VARCHAR(255),
    content_type VARCHAR(100),
    tags TEXT[],  -- Array of strings
    summary TEXT,
    url VARCHAR(255),
    project_name VARCHAR(255),
    indexing_status VARCHAR(50),
    filename VARCHAR(255),
    priority INTEGER,
    read_time FLOAT,  -- In minutes
    creation_date TIMESTAMPTZ,
    last_modified_date TIMESTAMPTZ,
    upload_date TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_doc_url_project UNIQUE (url, project_name),
    CONSTRAINT fk_project_name FOREIGN KEY (project_name) REFERENCES projects(name)
);

Content:
id,title,author,file_type,word_count,language,source,content_type,tags,summary,url,project_name,indexing_status,filename,priority,read_time,creation_date,last_modified_date,upload_date
8,AI Expertisecentrum,,webpage,408,NL,chrome_extension,blog_post,"[""AI"",""Vlaamse overheid"",""digitale transformatie"",""ethiek"",""kennisdeling""]",Het AI Expertisecentrum ondersteunt de Vlaamse overheid en lokale overheden in het gebruik van artificiële intelligentie om de efficiëntie en innovatie van diensten te verbeteren. Het centrum biedt een kader voor AI-toepassingen en stimuleert kennisdeling binnen de overheid.,https://www.vlaanderen.be/digitaal-vlaanderen/onze-oplossingen/ai-expertisecentrum,Test,,AI Expertisecentrum,,2.04,,,2024-09-03 16:27:05.904255+00
9,Wat betekent de aankomende NIS2-richtlijn (cybersecurity wetgeving)…,,webpage,889,NL,chrome_extension,blog_post,"[""Cybersecurity"",""NIS2"",""GDPR"",""Belgium"",""Government"",""Digital Security""]","The NIS2 directive, effective from October 2024 in Belgium, aims to enhance cybersecurity across Europe, impacting government leaders by imposing strict security standards similar to GDPR. It emphasizes the responsibility of organizations in managing digital security, requiring comprehensive risk management, incident response plans, and a culture of security awareness among employees.",https://www.vlaanderen.be/digitaal-vlaanderen/wat-betekent-de-aankomende-nis2-richtlijn-cybersecurity-wetgeving-voor-leidinggevenden-bij-de-overheid,Vlaamse Overheid,,Wat betekent de aankomende NIS2-richtlijn (cybersecurity wetgeving)…,,4.445,,,2024-09-03 16:30:03.524486+00
10,Vectrix Mail,,webpage,5070,EN,chrome_extension,email,"[""AI"",""Community"",""Event"",""Newsletter"",""Invitation""]","The content consists of various email communications regarding community events, invitations, confirmations, and newsletters related to AI and business activities. Key participants include Paulien Derden and Dimitri Allaert, with discussions about supporting an AI community in Antwerp, event invitations, and confirmations for conferences and meetings.",https://mail.google.com/mail/u/0/#search/bart/FMfcgzQVzNvVshgTnGNKFwPdtwZrsXNt,Vlaamse Overheid,,Vectrix Mail,,25.35,,,2024-09-03 16:32:39.998075+00
11,Vectrix - SLM Training & AI Solutions,,webpage,126,EN,webpage,other,"[""AI"",""Technology"",""Business"",""Product Development""]","The content discusses an AI solution development process, including initial discussions, feasibility checks, MVP development, and final product creation, emphasizing security, compliance, and user control.",https://vectrix.ai/,Vectrix,,,,0.63,,,2024-09-03 17:00:00.472415+00

Question: {input}"""
