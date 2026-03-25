import "./globals.css";
import { Providers } from "./providers";

// TODO: Update metadata with actual demo details
export const metadata = {
  title: "Multimodal Event Explorer",
  description: "MongoDB-powered multimodal search for autonomous driving and industrial scenarios"
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
