import "./App.css";
import { Login } from "./components/Login";

function App() {
  return (
    <>
      <div className="h-[100vh] grid place-items-center">
        <div className="w-full max-w-80">
          <Login />
        </div>
      </div>
    </>
  );
}

export default App;
