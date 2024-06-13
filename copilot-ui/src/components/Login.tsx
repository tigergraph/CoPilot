'use client'

import { useContext, createContext, useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { z } from 'zod'

import { Button } from '@/components/ui/button'
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormDescription,
  FormMessage,
} from '@/components/ui/form'
import { Input } from '@/components/ui/input';

import { LANGUAGES } from "../constants";


const formSchema = z.object({
  email: z.string().min(2, {
    message: 'Email must be at least 2 characters.',
  }),
  password: z.string().min(2, {
    message: 'Password must be at least 2 characters.',
  }),
})

const AuthContext = createContext();
const WS_URL = 'http://0.0.0.0:8000/ui/ui-login';

export function Login() {
  const { i18n, t } = useTranslation();
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem("site") || "");
  const navigate = useNavigate();

  // useEffect(() => {
  //   const fetchMe = async () => {
  //     try {
  //       const response = await fetch(WS_URL, {
  //         method: 'POST',
  //         headers: {
  //           // Authorization: token,
  //           Authorization: "Basic " + btoa('user_2' + ":" + 'Thisistheadmin!1')
  //         },
  //       });
  //       const res = await response.json();
  //       console.log(res);
  //       if (res) {
  //         setUser(res);
  //         return;
  //       }
  //       throw new Error(res.message);
  //     } catch (err) {
  //       console.error(err);
  //     }
  //   }
  //   fetchMe();
  // }, []);

  useEffect(() => console.log(localStorage), []);


  const loginAction = async (data: z.infer<typeof formSchema>) => {
    console.log(data);
    try {
      const response = await fetch(WS_URL, {
        method: "POST",
        headers: {
          Authorization: "Basic " + btoa(data.email + ":" + data.password),
          "Content-Type": "application/json",
        },
      });
      const res = await response.json();
      console.log(res);
      if (res) {
        setUser(res);
        setToken(res);
        localStorage.setItem("site", JSON.stringify(res));
        navigate("/chat");
        return;
      }
      throw new Error(res.message);
    } catch (err) {
      console.error(err);
    }
  };


  const logOut = () => {
    setUser(null);
    setToken("");
    localStorage.removeItem("site");
    navigate("/login");
  };


  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      email: '',
      password: '',
    },
  })


  const onChangeLang = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const lang_code = e.target.value;
    i18n.changeLanguage(lang_code);
  };


  return (
    <>
      <img src='./tg-logo-xl.svg' className='mx-auto mb-5' />

      <h1 className='text-center text-2xl font-bold mb-5'>{t("welcome")}<br />TigerGraph Bot</h1>
      <h4 className='text-center mb-10 text-black dark:text-[#D9D9D9]'>{t("login")}</h4>

      <Form {...form}>
        <form onSubmit={form.handleSubmit(loginAction)}>
          <FormField
            control={form.control}
            name='email'
            render={({ field }) => (
              <>
                <FormItem className='mb-5'>
                  <FormControl>
                    <Input placeholder={t("username")} {...field} className='dark:border-[#3D3D3D] py-6 dark:bg-shadeA' />
                  </FormControl>
                  <FormDescription></FormDescription>
                  <FormMessage />
                </FormItem>
              </>
            )}
          />
          <FormField
            control={form.control}
            name='password'
            render={({ field }) => (
              <>
                <FormItem className='mb-5'>
                  <FormControl>
                    <Input placeholder={t("password")}  type='password' {...field} className='dark:border-[#3D3D3D] py-6 dark:bg-shadeA' />
                  </FormControl>
                  <FormDescription></FormDescription>
                  <FormMessage />
                </FormItem>
              </>
            )}
          />
          <a href='#' className='text-xs text-right block'>{t("forgotPassword")}</a>
          <Button type='submit' className='gradient w-full text-white mt-10'>{t("submit")}</Button>
                      
          <div className="inline-flex items-center justify-center w-full">
            <hr className="w-full h-px my-8 border-0 bg-gray-200 dark:bg-gray-700" />
            <span className="absolute px-3 text-xs bg-background dark:border-[#3D3D3D] text-gray-900 -translate-x-1/2 left-1/2 dark:text-white">{t("noAccount")}</span>
          </div>
          
          <a href='#' className='text-xs text-center block !text-tigerOrange'>{t("signUp")}</a>
        </form>
      </Form>

      <select defaultValue={i18n.language} onChange={onChangeLang} className="rounded-lg border border-shadeA dark:bg-background dark:text-white absolute bottom-10 p-3 left-10">
        {LANGUAGES.map(({ code, label }) => (
          <option key={code} value={code}>
            {label}
          </option>
        ))}
      </select>

    </>
  )
}