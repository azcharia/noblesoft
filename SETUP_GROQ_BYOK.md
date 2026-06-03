# Setup Guide: Groq BYOK (Bring Your Own Key) in NobleSoft

NobleSoft supports isolated **Bring Your Own Key (BYOK)** architecture. Each tenant can configure their own Groq API Key to power the cashier AI assistant. By using pure Groq, we ensure ultra-low latency inference and maximum data privacy, avoiding OpenRouter's free-tier data training policies.

---

## 1. How to Get a Groq API Key

Follow these simple steps to obtain your API Key from the official Groq console:

1. **Sign Up / Log In**: Visit the [Groq Console](https://console.groq.com/) and register a free account.
2. **Access API Keys Page**: Once logged in, navigate to the **API Keys** section in the left-hand sidebar menu.
3. **Create Key**: Click the **"Create API Key"** button.
4. **Label Your Key**: Give your key a descriptive name (e.g., `NobleSoft-Cashier-AI`).
5. **Copy the Key**: Copy the generated API key immediately. 
   > [!IMPORTANT]
   > The API key starts with `gsk_`. Store it securely, as you will not be able to view it again on the Groq Console.

---

## 2. Configuring Groq in NobleSoft Dashboard

To link your Groq API Key to your store tenant workspace:

1. **Open Settings**: Log in to your NobleSoft dashboard and go to **Settings** -> **AI & API Settings** (or navigate to `/settings/ai` directly).
2. **Enter Credentials**:
   - **Groq API Key**: Paste the `gsk_...` key you copied from the Groq console.
   - **Custom Base URL (Optional)**: Leave this blank to use the official Groq API endpoint (`https://api.groq.com/openai/v1`). If you are using a reverse proxy or a custom OpenAI-compatible API gateway, you can input it here.
   - **Model Name**: By default, `llama-3.1-8b-instant` is pre-configured. It is highly recommended due to its ultra-fast response times. You can also specify other official Groq models like:
     - `llama-3.3-70b-specdec` (More intelligent, suitable for complex function calls)
     - `mixtral-8x7b-32768` (Good balance of speed and knowledge)
   - **Temperature**: Keep this at `0.2`. A lower temperature ensures the AI remains factual and precise, which is critical for handling stock updates and transactions.
3. **Test & Save**:
   - Click the **"Save Changes"** (Simpan Perubahan) button.
   - NobleSoft will automatically trigger a **live ping test** to verify your Groq API Key before saving.
   - If successful, your settings will be encrypted and saved securely in your dedicated tenant database.

---

## 3. Data Privacy & Architecture

- **Tenant Isolation**: Your Groq API key is encrypted and stored in a tenant-specific table. It is never shared with other tenants or used globally by the system.
- **Pure Groq Execution**: By bypassing OpenRouter free models, your transaction details are sent directly to Groq's high-speed inference engine under their developer privacy policy, ensuring your business data is not harvested for public model training.
- **Local Embedding Vectorizer**: The text-to-vector embeddings for your products and invoices are processed 100% locally on the hosting server using the `sentence-transformers/all-MiniLM-L6-v2` model. No external API calls are made to categorize or search your internal business data, keeping your inventory completely secure.
