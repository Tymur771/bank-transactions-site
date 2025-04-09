import { useState } from "react";

const transactions = [
  { date: "2024-11-08", description: "Maplebear, Inc", amount: 333.06 },
  { date: "2024-11-12", description: "Zelle from SARAH BUXTON", amount: 400.00 },
  { date: "2024-11-12", description: "Uber", amount: 35.76 },
  { date: "2024-11-13", description: "Zelle from STANISLAV IVAKHNIENKO", amount: 400.00 },
  { date: "2024-11-29", description: "PNM*Santander", amount: -695.11 },
  { date: "2024-12-03", description: "VENMO*Deina Ty", amount: 589.50 },
  { date: "2024-12-09", description: "Zelle from MIKHAIL NESVAT", amount: 400.00 },
  { date: "2024-12-09", description: "OPENAI *CHATGPT SUBSCR", amount: -23.80 },
];

export default function Home() {
  const [search, setSearch] = useState("");

  const filtered = transactions.filter(tx =>
    tx.description.toLowerCase().includes(search.toLowerCase())
  );

  const totalIncome = filtered.filter(tx => tx.amount > 0).reduce((sum, tx) => sum + tx.amount, 0);
  const totalExpense = filtered.filter(tx => tx.amount < 0).reduce((sum, tx) => sum + tx.amount, 0);

  return (
    <div style={{ padding: "2rem", fontFamily: "Arial, sans-serif" }}>
      <h1>Bank Transactions</h1>
      <input
        type="text"
        placeholder="Search by description..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        style={{ padding: "0.5rem", marginBottom: "1rem", width: "100%" }}
      />
      <div style={{ marginBottom: "1rem" }}>
        Showing {filtered.length} results | Income: ${totalIncome.toFixed(2)} | Expenses: ${Math.abs(totalExpense).toFixed(2)}
      </div>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr>
            <th style={{ borderBottom: "1px solid #ccc", textAlign: "left" }}>Date</th>
            <th style={{ borderBottom: "1px solid #ccc", textAlign: "left" }}>Description</th>
            <th style={{ borderBottom: "1px solid #ccc", textAlign: "right" }}>Amount</th>
          </tr>
        </thead>
        <tbody>
          {filtered.map((tx, index) => (
            <tr key={index}>
              <td>{tx.date}</td>
              <td>{tx.description}</td>
              <td style={{ textAlign: "right" }}>{tx.amount > 0 ? `+$${tx.amount.toFixed(2)}` : `-$${Math.abs(tx.amount).toFixed(2)}`}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}