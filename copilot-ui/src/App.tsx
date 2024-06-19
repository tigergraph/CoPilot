import "./App.css";
import { useEffect, useState } from "react";
import { Login } from "./components/Login";

function App() {
  // const [isAuth, setIsAuth] = useState(false);

  // useEffect(() => {
  //   if (isAuth) {
  //     window.location.href = '/chat';
  //   }
  // }, [isAuth]);

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
