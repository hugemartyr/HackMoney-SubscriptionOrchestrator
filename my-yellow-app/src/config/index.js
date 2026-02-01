import "dotenv/config";

export const config = {
  privateKey: process.env.PRIVATE_KEY,
  clearnodeUrl:
    process.env.CLEARNODE_URL || "wss://clearnet-sandbox.yellow.com/ws",
};
