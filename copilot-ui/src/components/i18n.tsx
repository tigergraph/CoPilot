import i18n from "i18next";
import { initReactI18next } from "react-i18next";

i18n
  // .use(i18nBackend)
  .use(initReactI18next)
  .init({
    fallbackLng: "en",
    lng: "en",
    interpolation: {
      escapeValue: false,
    },
    resources: {
      en: {
        translation: {
          welcome: "Welcome to",
          login: "Please log in to your TigerGraph account to continue.",
          username: "Username",
          password: "Password",
          forgotPassword: "Forgot Password",
          submit: "Submit",
          noAccount: "Don't have an account?",
          signUp: "Sign Up"
        },
      },
      es: {
        translation: {
          welcome: "Bienvenido a",
          login: "Inicie sesión en su cuenta TigerGraph para continuar.",
          username: "Nombre de usuario",
          password: "contraseña",
          forgotPassword: "¿Has olvidado tu contraseña?",
          submit: "Entregar",
          noAccount: "¿No tienes una cuenta?",
          signUp: "Regístrate"
        },
      },
    },
  });

export default i18n;







