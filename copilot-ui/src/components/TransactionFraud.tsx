import { FC, useState } from 'react';
import { useTheme } from "@/components/ThemeProvider"

interface Start {
    props: any;
    setState: any;
    actionProvider: any,
    actions: any
    fullPage: any
}

export const TransactionFraud: FC<Start> = (props) => {
    const [visibility, setVisibility] = useState(true);
    const getTheme = useTheme().theme;

    const defaultQuestions = (msg: string) => {
      props.actions.defaultQuestions(msg);
      setVisibility(false);
    }

    return (
      <>
        <div className='ml-[50px]'>
          <ol>
            <h1 className='mb-5 text-lg'>1. Financial Transactions</h1>
            <p className='block mb-5'>Financial transactions involve the exchange of money between parties. Key aspects include:</p>
            - Parties Involved: The buyer and the seller.<br/>
            - Medium of Exchange: Cash, checks, credit cards, electronic transfers.<br/>
            - Types: Purchase of goods/services, investment, loan issuance, etc.<br/>
            - Records: Documented through receipts, invoices, bank statements.
          </ol>
        </div>
        <img src='chart.svg' className="mx-auto mb-5 mt-10" />

        {/* <img src='tg-logo-xl.svg' className="mx-auto mb-5 mt-10" />
        <h1 className="text-center text-2xl font-bold mb-10 dark:text-white">How can I help you?</h1>
        
        <div className="grid gap-4 grid-cols-1 md:grid-cols-2 mb-10">
          {questions.map((question, i) => (
            <div key={i} className={`rounded-lg border dark:bg-shadeA dark:border-none px-5 py-4 text-sm ${props.fullPage ? 'h-[84px] flex justify-between items-center' : 'flex grow flex-col'}`}>
              <span className={`${props.fullPage ? '' : 'mb-5'} block`}>{question.title}</span>
              <div
                className={`rounded-lg bg-[#ececec] w-[75px] flex justify-center items-center p-2 hover:bg-slate-300 cursor-pointer dark:text-black ${props.fullPage ? '' : 'mt-auto'}`} 
                onClick={() => defaultQuestions(`${question.title}`)}>
                  <HiOutlineChatBubbleOvalLeft className="mr-1 dark:text-black" />Ask
              </div>
            </div>
          ))}
        </div> */}
      </>
    )
}
