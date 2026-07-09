# 🌟 AI-Based Automated Data Cleaning & Deduplication Tool 
**Complete Non-Technical Documentation**

---

## 1. About the Project (Project ke baare mein)
Aaj kal businesses ke paas bahut saara data hota hai, lekin wo data aksar "ganda" (dirty) hota hai — yani usme spelling mistakes hote hain, duplicate entries hoti hain, alag-alag languages (jaise Hindi aur English) mix hoti hain, aur kuch details missing hoti hain.

Yeh project ek **AI (Artificial Intelligence) based software** hai jo kisi bhi kharab, messy Excel ya CSV data ko automatically samajhta hai aur use ekdum clean, perfect aur useable data mein convert kar deta hai. Yeh tool insaano ki tarah data ko padhta hai, samajhta hai aur khud decision leta hai ki kya theek karna hai.

### Features (Isme kya khaas hai?)
- **Smart AI Brain:** Ye sirf rules pe nahi chalta, balki LLM (jaise ChatGPT) ka use karke samajhta hai ki aapka data kis baare mein hai (e.g. Retail, Healthcare, Finance).
- **Multilingual Support:** Agar naam "Rahul" hai aur ek entry "राहुल" hai, toh ye unhe samajh kar ek kar deta hai.
- **Advanced Deduplication:** "IBM" aur "International Business Machines" jaise complex duplicates ko ek pehchanta hai aur merge karta hai.
- **Smart Imputation:** Agar koi data missing hai, toh ye bache hue data ka pattern dekh kar missing details ko automatically fill kar deta hai.
- **Currency Conversion:** Agar data mein ₹, $, €, sab mix hain, toh ye automatically latest exchange rate se sabko INR (₹) mein convert kar deta hai.

### Importance (Ye kyun zaroori hai?)
Galat data se business ke decisions galat ho sakte hain. Duplicate emails se ek hi customer ko 5 baar email ja sakti hai, jisse company ki image kharab hoti hai. Ye tool hours/days ka manual data cleaning work sirf kuch seconds mein perfectly kar deta hai bina kisi error ke.

---

## 2. Types of Data Cleaning (Ye kya-kya saaf kar sakta hai?)
Is project mein **Data Cleaning Pipeline** banayi gayi hai jisme data kai stages se guzarta hai:

1. **String Pre-cleaning:** Faltu spaces, special characters, aur capitalization theek karna.
2. **Missing Values Imputation:** Khali dabbon (null values) ko logic aur AI ki madad se bharna.
3. **Multilingual Transliteration:** Hindi ya kisi aur script ko standard English characters mein convert karna taaki match karne mein aasaani ho.
4. **Currency Standardization:** Har tarah ke paiso ki values ko pehchanna aur ek standard (jaise ₹) mein convert karna.
5. **Deduplication (Entity Resolution):** Har tarah ke duplicates hatana:
   - *Exact Duplicates:* Jo ekdum same hain.
   - *Fuzzy Duplicates:* Type karne mein mistake ("Samip" vs "Sameep").
   - *Cross-Language:* "Amit" aur "अमित".
   - *Semantic Duplicates:* Matlab same hai lekin word alag.
6. **Outlier Detection:** Aise data points ko hatana ya flag karna jo baaki data se bilkul alag (abnormal) hain.

---

## 3. Project Folder Structure (Project ki files kaise arranged hain?)
Project ke main parts ye hain:
- `app.py`: Ye Frontend hai. Jo beautiful user interface (UI) aapko dikhta hai, jahan aap file upload karte hain, wo is file se chalta hai.
- `backend/pipeline.py`: Ye "Engine" hai. Jab aap "Clean Data" dabate hain, toh ye file saare cleaning tasks ko line se chalati hai.
- `agents/`: Is folder mein AI Agents (Specialized LLM tools) ki files hain jo alag-alag dimagi kaam karte hain.
- `cleaning/`: Isme specific data saaf karne ke tools hain (jaise currency convertor, deduplicator, waghera).

---

## 4. AI Agents Explanations (Kaunsa AI Agent kya karta hai?)

Project mein alag-alag AI "workers" (agents) hain jinka apna specific kaam hai. Chaliye inhe aasaan bhasha mein samajhte hain:

### 🧠 Schema Agent (`schema_agent.py`)
- **Iska kya upyog hai? (What is its use?)**
  Jaise hi aap data upload karte hain, sabse pehle Schema Agent us data ko dekhta hai aur samajhta hai ki columns ka matlab kya hai (Data ki kundli nikalta hai).
- **Kaise kam karta hai? (How does it work?)**
  Ye dataset ka ek chota sa sample uthata hai aur use analyze karta hai. 
- **Isme kya logic hai jiska use karke LLM detect karta hai?**
  LLM columns ke naam (jaise 'emp_id', 'DOB') aur unke andar ke actual data (jaise '12/03/1990') ko padhta hai. Wo apne knowledge se classify karta hai ki ye dataset "Healthcare" ka hai, "Finance" ka hai ya "Retail" ka hai. Sath hi wo batata hai ki kaunsa column ID hai, kaunsa Name hai, aur kaunsa personally identifiable hai jisko aage mix nahi karna chahiye.
- **Phir next agent ko kya message jata hai?**
  Ye ek "Schema Mapping" document banata hai jisme har column ki identity hoti hai. Ye mapping report aage Planner Agent aur dusre tools ko pass ki jati hai taaki wo us hisaab se cleaning rules lagayein.

### 📋 Planner Agent (`planner_agent.py`)
- **Iska kya upyog hai? (What is its use?)**
  Ye project ka 'Manager' hai. Schema Agent ne jo bataya, uske basis par ye plan banata hai ki data ko kaise theek karna hai.
- **Kaise kam karta hai?**
  Agar data mein missing values hain, toh ye LLM ka use karke smart "If-Else" business rules banata hai. 
- **Isme kya logic hai?**
  LLM pure data ke trends ko dekhta hai. Maan lijiye 'Company Size' missing hai, lekin 'Revenue' bahut bada hai, toh LLM logic lagata hai ki: *"IF Revenue is greater than 1 Million, THEN Company Size should be 'Large'"*. Ye logic ye khud generate karta hai!
- **Phir next agent ko kya message jata hai?**
  Ye apna banaya hua step-by-step master plan `missing_values.py` aur `deduplication.py` jaise cleaning modules ko bhej deta hai taaki wo data saaf karna shuru karein.

### 🔗 Deduplication Engine (`deduplication.py`)
*(Ye technical module hai, lekin ek AI ki tarah kam karta hai)*
- **Iska kya upyog hai?**
  Ye ensure karta hai ki ek hi insaan ya company ki 2 alag-alag entries data mein na ho. 
- **Kaise kam karta hai?**
  Ye ek bahut advance pipeline chalata hai: Pehle direct match karta hai (IDs, Email). Phir spelling mistakes (Fuzzy match) dekhta hai. Agar naam lagabhag same hai (jaise "Sameep" aur "Samip") toh ye unhe merge kar deta hai. Isme Business Rules bhi lagte hain jo conflicts ko block karte hain (e.g. agar Naam same hai lekin Country alag hai, toh merge mat karo).

### 🗣️ Explanation Agent (`explanation_agent.py`)
- **Iska kya upyog hai?**
  Jab pipeline background mein koi complex decision leti hai (jaise 2 rows ko merge kar diya), toh user ko kaise pata chalega ki ye kyun kiya gaya? Explanation Agent ka kaam hai machine ki language ko normal insaani bhasha mein samjhana.
- **Kaise kam karta hai?**
  Ye agent backend ke technical logs aur change records (jaise "Cluster 3 merged due to Jaro-Winkler score 0.94") ko padhta hai, aur ek normal human language mein explanation generate karta hai (jaise "Aapke data mein 2 records the jinki spelling mein slight mistake thi, par email same hone ki wajah se unhe ek maan liya gaya").

### 🔍 Validation Agent (`validation_agent.py`)
- **Iska kya upyog hai?**
  Data pura clean hone ke baad, final checking karna, jaise quality inspector karta hai.
- **Kaise kam karta hai?**
  Ye final cleaned dataset ko dekhta hai aur purane schema (jo pehle Agent ne banaya tha) se match karta hai. Ye check karta hai: Kya koi zaroori ID column galti se delete ho gaya? Kya age negative mein chali gayi? Agar sab sahi hota hai toh ye "Green Signal" deta hai, warna "Warnings" (alerts) generate karke frontend par UI ko bhej deta hai ki kahan gadbadi bachi hai.

### 💬 NL Query Agent (Natural Language Chat Agent) (`nl_query_agent.py`)
- **Iska kya upyog hai?**
  Ye data cleaning hone ke baad data ke upar "Chatbot" ka kaam karta hai. Aap apne data se direct baatein kar sakte hain.
- **Kaise kam karta hai?**
  Agar user puchta hai "Give me the list of top 5 customers from Delhi", toh NL Query agent LLM ka use karke is English sentence ko samajhta hai. Phir ye khud ek Pandas (Python) ka code generate karta hai, us code ko aapke saaf kiye hue data par chalata hai, aur jo answer aata hai usko chart ya normal language mein translate karke aapko wapas bhej deta hai.

---

## 5. Summary Flow (Kaam Aakhir Hota Kaise Hai?)
1. **User** file upload karta hai.
2. **Schema Agent** data ki pehchan karta hai (Intelligent mapping).
3. **Planner Agent** sochta hai ki isko saaf kaise karna hai aur AI-rules banata hai.
4. **Cleaning Modules** (Multilingual, Currency, Deduplication) apna-apna specific saaf-safai ka kaam karte hain.
5. **Validation Agent** final data ko check karta hai.
6. **Explanation Agent** report banata hai ki usne kya aur kyun kiya.
7. End mein, user **NL Query Agent** se chat karke saaf data ko analyze kar sakta hai.

Is tarah, ek highly messy aur unorganized data bina kisi manual code likhe, ekdum clean, deduplicated aur structured database mein convert ho jata hai!
