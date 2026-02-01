// import { ethers } from "ethers";
// import dotenv from "dotenv";

// dotenv.config();

// export default async function setupMessageSigner() {
//   const { PRIVATE_KEY, RPC_URL } = process.env;

//   if (!PRIVATE_KEY) {
//     throw new Error("PRIVATE_KEY not found in .env");
//   }

//   // Create provider
//   const provider = new ethers.JsonRpcProvider(RPC_URL);

//   // Create wallet signer
//   const wallet = new ethers.Wallet(PRIVATE_KEY, provider);

//   const userAddress = wallet.address;

//   // Message signer function
//   const messageSigner = async (message) => {
//     return await wallet.signMessage(message);
//   };

//   console.log("✅ Wallet loaded:", userAddress);

//   return { userAddress, messageSigner };
// }

import { Wallet, JsonRpcProvider } from "ethers";
import dotenv from "dotenv";
dotenv.config();

export async function setupWallet() {
  const provider = new JsonRpcProvider(process.env.RPC_URL);
  const wallet = new Wallet(process.env.PRIVATE_KEY, provider);

  return {
    userAddress: wallet.address,
    messageSigner: async (message) => wallet.signMessage(message),
  };
}
