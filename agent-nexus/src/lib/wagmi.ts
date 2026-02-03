import { getDefaultConfig } from "@rainbow-me/rainbowkit";
import { http } from "viem";
import { mainnet, sepolia, polygon, base } from "wagmi/chains";

const projectId = import.meta.env.VITE_WALLETCONNECT_PROJECT_ID ?? "demo";

export const chains = [mainnet, sepolia, polygon, base] as const;

export const wagmiConfig = getDefaultConfig({
  appName: "Meta-Agent Factory",
  projectId,
  chains,
  transports: {
    [mainnet.id]: http(),
    [sepolia.id]: http(),
    [polygon.id]: http(),
    [base.id]: http(),
  },
});
