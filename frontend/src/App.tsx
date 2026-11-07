import { useEffect, useState } from "react";

import { client } from "./api/client.gen";
import { apiHealth } from "./api/sdk.gen";

client.setConfig({ baseUrl: "" });

export default function App() {
  const [status, setStatus] = useState("loading…");

  useEffect(() => {
    apiHealth()
      .then(({ data }) => setStatus(data?.status ?? "unknown"))
      .catch(() => setStatus("unavailable"));
  }, []);

  return (
    <main>
      <h1>Календарь звонков</h1>
      <p>Статус API: {status}</p>
    </main>
  );
}
