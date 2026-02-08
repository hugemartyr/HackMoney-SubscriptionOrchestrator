import { getDefaultConfig } from "@rainbow-me/rainbowkit";
import { http } from "wagmi";
import { mainnet, sepolia, polygon, base } from "wagmi/chains";

const projectId = "3a8170812b534d0ff9d794f19a901d64"; // Using a public demo ID or env var

export const config = getDefaultConfig({
  appName: "Yellow Agent",
  projectId,
  chains: [mainnet, sepolia, polygon, base],
  ssr: true,
  transports: {
    [mainnet.id]: http(),
    [sepolia.id]: http(),
    [polygon.id]: http(),
    [base.id]: http(),
  },
});
