
Make a recipe for integrating meshconnect with anchor in a box for deposits (taking funds from an exchange onto stellar) with all examples using curl and jq


Given this docs.. make a list of calls that would be useful for integrating anchor in a box.

Just list the commands as curl commands with jq and a short explanation that a developer could look at.

For the front end (sep24 de

Docs

https://docs.meshconnect.com/manual




====================
Example request and response that works
 curl --request GET \
  --url https://sandbox-integration-api.meshconnect.com/api/v1/transfers/managed/networks \
  --header 'X-Client-Id: 358ef0a7-9d16-4b55-966a-08ddde81b87e' \
  --header 'X-Client-Secret: sk_sand_0yxjryt8.tsdg8qwcg4tn170a7rs37po9gq5cddvsnhpby8iijstkhs6e6fzfc9ztm9xebndy' \
  | jq '.content.networks[] | select(.name == "Stellar")'

{
  "networkType": "stellar",
  "tokens": [
    {
      "symbol": "EURC",
      "logoUrl": "https://file-cdn.meshconnect.com/public/logos/tokens/EURC.svg"
    },
    {
      "symbol": "USDC",
      "logoUrl": "https://file-cdn.meshconnect.com/public/logos/tokens/USDC.svg"
    },
    {
      "symbol": "XLM",
      "logoUrl": "https://file-cdn.meshconnect.com/public/logos/tokens/XLM.svg"
    }
  ],
  "supportedBrokerTypes": [
    "robinhood",
    "coinbase",
    "binanceUs",
    "binanceInternational",
    "huobi",
    "krakenDirect",
    "binanceInternationalDirect",
    "bitfinexDirect",
    "bybit",
    "btcTurkDirect",
    "binanceConnect",
    "revolutConnect",
    "bybitDirect",
    "paribuOAuth",
    "coinbaseRamp",
    "sandbox"
  ],
  "supportedTokens": [
    "EURC",
    "USDC",
    "XLM"
  ],
  "nativeSymbol": "XLM",
  "id": "06855704-43d2-4ad2-a73c-372f0c3534e1",
  "name": "Stellar",
  "logoUrl": "https://file-cdn.meshconnect.com/public/logos/networks/Stellar.svg"
}

====================




Manual
This guide provides a step-by-step walkthrough for integrating the Mesh SDK across all supported platforms. The core flow is the same everywhere: your secure backend creates a linkToken, which your client-side application then uses to open the Link UI.
​
Setting up your developer dashboard (team members, API keys, and Link customization)

    Go to Account > Team to add team members. New team members can be invited with varying permission sets to ensure you control access to only what’s needed on a per-member basis.

Image1 Pn

    Go to Account > API keys to add callback URLs (where the Mesh SDK will be allowed to render) and to generate your production or sandbox API keys (you’ll have to complete a business verification check before being able to generate production keys).

Image2 Pn

    Go to Account > Link configuration to customize the Link SDK for your branding and other needs.

Image3 Pn
​
Create Link Token (Backend)
This first step is a mandatory server-side operation and is the same for all client platforms. The Link UI is always initialized with a linkToken, which must be generated from your backend to protect your apiSecret. 🔒 Security First Never expose your X-Client-Secret in a client-side application. The /api/v1/linktoken endpoint must always be called from a secure server environment. Make a POST request from your backend to the appropriate Mesh API endpoint: Sandbox: https://sandbox-integration-api.meshconnect.com Production: https://integration-api.meshconnect.com Example cURL request from your backend

curl --request POST \
     --url https://integration-api.meshconnect.com/api/v1/linktoken \
     --header 'accept: application/json' \
     --header 'content-type: application/json' \
     --header 'X-Client-Id: YOUR_CLIENT_ID' \
     --header 'X-Client-Secret: YOUR_CLIENT_SECRET' \
     --data '{
        "userId": "example_user123",
  		"restrictMultipleAccounts": true,
  		"transferOptions": {
    		"transactionId": "example_tx123",
    		"transferType": "payment", // payment or deposit
    		// Enable SmartFunding
    		"fundingOptions": {
      			"enabled": true
    		},
    	"isInclusiveFeeEnabled": false,
    	"toAddresses": [
      		{
        		"symbol": "USDT",
        		"address": "0x314838D6783865908456257c0b07Ea4Bc272cF98", 
        		"networkId": "18fa36b0-88a8-43ca-83db-9a874e0a2288",
        		"amount": 99.99 // pass an amount when enabling SmartFunding
      		}
    	]
      }'

The API will respond with a linkToken that you can then send to your client application.
​
Configuring the Link Token
The linkToken is a powerful tool that allows you to tailor the Link UI for your specific use case. By passing different parameters in the body of your POST /api/v1/linktoken request, you can control the entire user journey.
​
Setting up a Transfer
If you want the user to transfer assets, you must include the transferOptions object in your request body. This object contains all the necessary details for the transaction.
​
Finding the networkId
The networkId is a required field that tells Mesh which blockchain to use for the transfer. You can retrieve a complete list of all supported networks and their corresponding networkId values by making a GET request to our transfers/managed/networks endpoint.
​
Configuring Destination Addresses (toAddresses)
This array tells Mesh where the user can send their funds.

    Single Address (Streamlined UX): If your user has already selected a token and network in your app, or if you only accept one specific asset, you can pass a single object in the toAddresses array. This provides the most direct user experience, as Link will skip the asset and network selection screens.
    Multiple Addresses (Recommended for Flexibility): For greater flexibility and potentially higher conversion, we recommend passing an array of all possible tokens and networks that you accept. This allows the user to choose their preferred asset within the Link UI.

​
Enabling SmartFunding
To maximize conversion and increase average transfer size, you should always enable SmartFunding.

    How to Enable: Set enabled: true within the fundingOptions object inside transferOptions.
    Why it’s important: SmartFunding allows users to complete a payment even if they don’t have enough of the target asset by auto-converting their other available tokens. This is a key feature for ensuring a successful transaction.

"transferOptions": {
  "toAddresses": [
    // ... your single or multiple addresses here
  ],
  "fundingOptions": {
    "enabled": true
  }
}

​
Controlling the User Flow
You can control where the user lands when the Link UI opens.

    Go to Catalog: By default, if you only provide a userId, the user will see the full catalog of supported exchanges and wallets.
    Go Straight to an Integration: To bypass the catalog and send the user directly to a specific institution (e.g., Coinbase), include the integrationId in your linkToken request.

​
Using Paylinks
If you want to simplify your integration and avoid using the client-side SDKs, you can use Paylinks. This feature generates a unique, Mesh-hosted URL that you can redirect your customers to.

    How to Enable: Set "generatePayLink": true inside your transferOptions.
    Learn More: For a detailed guide on this feature, please see our Paylinks Documentation.

​
Open Link UI (Client-Side)
Once your client application receives the linkToken, you can use it to initialize and open the Link UI. Installation

    Web
    iOS
    Android
    React Native

npm install --save @meshconnect/react-native-link-sdk

# Also ensure react-native-webview is installed
npm install --save react-native-webview

Code Implementation

    Web
    iOS
    Android
    React Native

import { createLink } from "@meshconnect/web-link-sdk";

// Initialize the Link connection with your callbacks
const meshLink = createLink({
  clientId: "YOUR_CLIENT_ID",
  onIntegrationConnected: (payload) => { /* Handle success */ },
  onExit: (error) => { /* Handle exit */ },
  onTransferFinished: (payload) => { /* Handle transfer result */ }
});

// Use the linkToken from your server to open the UI
meshLink.openLink("YOUR_LINK_TOKEN");

​
Handle Events
Your application needs to respond to events to know the outcome of a user’s session. This happens in two places: on the client-side from the SDK, and on the server-side from webhooks. From Link UI (Client-Side) The client-side SDK provides immediate feedback about the user’s interaction. Please see the Mesh Link SDK events guide for full details on callback functions and events emitted from Mesh’s SDKs.

    Web
    iOS
    Android
    React Native

The createLink function takes callbacks as arguments:

    onIntegrationConnected: Called on a successful account connection. The payload contains the accessToken.
    onTransferFinished: Called when a transfer is complete (either success or failure).
    onExit: Called when the user closes the UI.

From Webhooks (Server-Side) Webhooks are the definitive source of truth for the status of a transfer. While the client-side onTransferFinished event provides immediate feedback, a webhook from Mesh ensures your backend is notified of the final state (succeeded or failed), even if the user closes the app. Retrieving Historical Data To retrieve a history of past transfers and their final statuses, you can also use the GET /v1/transfers/managed/mesh endpoint. This is useful for reconciliation or auditing purposes after a transfer has already completed. You can find the API reference for this endpoint here. ➡️ Learn More For detailed information on webhook security, payload structure, and how to respond to events, see the webhooks guide. To get more information about our SDKs, refer to the respective Github repository:
Web	Android	iOS	React Native
​
Productionize
When you are ready to move from testing to production, follow these steps: Switch API Keys: In your Mesh Dashboard, generate Production API keys and use them in your backend environment variables. Update API Endpoint: Change the base URL in your backend from the sandbox endpoint to the production endpoint (https://integration-api.meshconnect.com). Configure Production Webhooks: In the Mesh Dashboard, add your production webhook URL to receive real-time transfer status updates. Add Allowed Callback URLs: Ensure your production domain (e.g., https://yourapp.com) is added to the “Allowed callback URLs” list in your dashboard settings to allow the Link SDK to load correctly.

Was this page helpful?
===========

Lets create a new git Branch 2025-meshconnect

make a plan to create a new sep24 integration for deposit with a form that supports Mesh

meshconnect.com
client id: 358ef0a7-9d16-4b55-966a-08ddde81b87e
miS0yohF)

/api/v1/linktoken endpoint must always be called from a secure server environment. Make a POST request from your backend to the appropriate Mesh API endpoint: Sandbox: https://sandbox-integration-api.meshconnect.com

Dedicated API Endpoint: Access the Sandbox API at: https://sandbox-integration-api.meshconnect.com.

Sandbox key BPVT1:sk_sand_0yxjryt8.tsdg8qwcg4tn170a7rs37po9gq5cddvsnhpby8iijstkhs6e6fzfc9ztm9xebndy

curl --request GET \
  --url https://sandbox-integration-api.meshconnect.com/api/v1/transfers/managed/networks \
  --header 'X-Client-Id: 358ef0a7-9d16-4b55-966a-08ddde81b87e' \
  --header 'X-Client-Secret: sk_sand_0yxjryt8.tsdg8qwcg4tn170a7rs37po9gq5cddvsnhpby8iijstkhs6e6fzfc9ztm9xebndy'


Notes
- funds will go directly to customers wallet - they will not go mesh -> anchor -> wallet
- use mesh 
- allow deposit of Stellar	3	XLM, USDC, EURC
- Coinbase	14	44+	US Market Leader + EMEA
Binance	17	58+	Global Coverage

https://docs.meshconnect.com/advanced/configuring-transfer-options
Core Components of transferOptions
Parameter	Type	Description
toAddresses	 this will be the wallet authenticated using SEP10
transferType	String	deposit.
fundingOptions	Object	SmartFunding.
transactionId	String	A unique identifier for the transaction from your system, crucial for reconciliation. Maybe we can use the memo?
ClientFee	Number	0 for now - but this should come from the configuration django local settings

=================

Docs:

Sandbox

Learn about the Sandbox environment, its features, limitations, and how to use it for API testing.
​
What is the Sandbox?
The Sandbox is a dedicated testing environment that allows you to integrate and interact with our APIs in a safe and controlled manner. It is designed to mirror the Production environment but uses mocked data for exchange integrations and testnet funds for wallet transactions, ensuring a realistic experience without risking real assets.
​
Key Features of the Sandbox

    Isolated from Production: Prevents any interference with your live application.
    Mocked Exchange Data: Simulates responses from centralized exchanges for testing API calls and transfer flows.
    On-Chain Wallet Testing: Supports the Sepolia testnet for validating real on-chain transactions with self-custody wallets.
    Dedicated API Endpoint: Access the Sandbox API at: https://sandbox-integration-api.meshconnect.com.

​
How to Test in the Sandbox: A Step-by-Step Guide

    ‼️ Important: For Development & Testing Only The Sandbox environment and Sandbox API keys are designed exclusively for your development and testing phases. Never use the Sandbox API endpoint or Sandbox keys in your live production application. Your production application must use your Production API keys and the production endpoint. 

​
Step 1: Get Your Sandbox API Keys
Before you begin, you must generate API keys specifically for the Sandbox.

    Go to Account > API keys in your Mesh Dashboard.
    Generate a new key in the “Sandbox” section. Remember to store your Client Secret securely.

​
Step 2: Test a Centralized Exchange (CEX) Transfer
This flow uses mocked data to simulate a transfer from an exchange like Coinbase or Binance.

    Generate a linkToken: From your backend, make a POST request to the Sandbox endpoint (https://sandbox-integration-api.meshconnect.com/api/v1/linktoken). Include a transferOptions object specifying a destination address.
    Initialize the Link SDK: Pass the linkToken to your client-side SDK to open the Link UI.
    Select an Exchange: In the Link UI, choose any supported exchange. You can use any credentials (e.g., “user123”/“pass123”) as the data is mocked.
    Complete the Transfer: Follow the on-screen prompts to initiate and confirm the transfer.
    Verify the Webhook: After completing the flow, you should receive a webhook notification with a succeeded status for the simulated transfer.

​
Step 3: Test a Self-Custody Wallet Transfer (On-Chain)
This flow uses the Sepolia testnet to validate a real on-chain transaction without risking actual funds.

    Get Sepolia ETH: To perform a testnet transaction, you need testnet tokens. You can get free Sepolia ETH from a public faucet. A reliable option is the Google Cloud Faucet: https://cloud.google.com/application/web3/faucet/ethereum/sepolia. Send these funds to a test wallet that you control, such as a test MetaMask account.
    Generate a linkToken: From your backend, make a POST request to the Sandbox endpoint. In the transferOptions, specify the Sepolia network and a destination address you own.
        Token: Sepolia ETH
        Network: Sepolia
    Initialize the Link SDK: Pass the linkToken to your client-side SDK.
    Select a Supported Wallet: In the Link UI, choose one of the supported testnet wallets, such as MetaMask or Rainbow. Connect the test wallet that holds your Sepolia ETH.
    Confirm the Transaction: You will be prompted by your wallet to sign and approve the on-chain transaction.
    Verify the Webhook & On-Chain Transaction: You will receive a webhook notification once the transaction is confirmed on the Sepolia network. You can also verify this by checking a Sepolia block explorer.



