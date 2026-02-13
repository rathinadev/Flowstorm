function App() {
  return (
    <div className="min-h-screen bg-flowstorm-bg text-flowstorm-text">
      <header className="border-b border-flowstorm-border px-6 py-4">
        <h1 className="text-2xl font-bold text-flowstorm-primary">
          FlowStorm
        </h1>
        <p className="text-sm text-flowstorm-muted">
          Self-Healing Stream Processing Engine
        </p>
      </header>
      <main className="p-6">
        <p className="text-flowstorm-muted">Pipeline editor loading...</p>
      </main>
    </div>
  );
}

export default App;
