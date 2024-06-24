import { FC, useState, useEffect } from "react";
import { MyDiagram } from "./graphs/ReaGraph";

const mockData = {
  "natural_language_response": "The card with ID 4218196001337 has more than 800 transactions from 2021-04-01 to 2021-08-01, with a total of 870 transactions.",
  "answered_question": true,
  "response_type": "inquiryai",
  "query_sources": {
      "function_call": "runInstalledQuery('card_has_frequent_transactions', params={'min_createTime': '2021-04-01', 'max_createTime': '2021-08-01', 'freq' : 800 })",
      "result": "[{\"rlt\": [{\"v_id\": \"4218196001337\", \"v_type\": \"Card\", \"attributes\": {\"rlt.@count\": 870}}]}, {\"@@edges\": [{\"e_type\": \"Card_Send_Transaction\", \"from_id\": \"4218196001337\", \"from_type\": \"Card\", \"to_id\": \"734576\", \"to_type\": \"Payment_Transaction\", \"directed\": false, \"attributes\": {}}, {\"e_type\": \"Card_Send_Transaction\", \"from_id\": \"4218196001337\", \"from_type\": \"Card\", \"to_id\": \"23414\", \"to_type\": \"Payment_Transaction\", \"directed\": false, \"attributes\": {}}, {\"e_type\": \"Card_Send_Transaction\", \"from_id\": \"4218196001337\", \"from_type\": \"Card\", \"to_id\": \"734581\", \"to_type\": \"Payment_Transaction\", \"directed\": false, \"attributes\": {}}, {\"e_type\": \"Card_Send_Transaction\", \"from_id\": \"4218196001337\", \"from_type\": \"Card\", \"to_id\": \"23415\", \"to_type\": \"Payment_Transaction\", \"directed\": false, \"attributes\": {}}, {\"e_type\": \"Card_Send_Transaction\", \"from_id\": \"4218196001337\", \"from_type\": \"Card\", \"to_id\": \"23409\", \"to_type\": \"Payment_Transaction\", \"directed\": false, \"attributes\": {}}, {\"e_type\": \"Card_Send_Transaction\", \"from_id\": \"4218196001337\", \"from_type\": \"Card\", \"to_id\": \"23411\", \"to_type\": \"Payment_Transaction\", \"directed\": false, \"attributes\": {}}, {\"e_type\": \"Card_Send_Transaction\", \"from_id\": \"4218196001337\", \"from_type\": \"Card\", \"to_id\": \"23413\", \"to_type\": \"Payment_Transaction\", \"directed\": false, \"attributes\": {}}, {\"e_type\": \"Card_Send_Transaction\", \"from_id\": \"4218196001337\", \"from_type\": \"Card\", \"to_id\": \"734578\", \"to_type\": \"Payment_Transaction\", \"directed\": false, \"attributes\": {}}, {\"e_type\": \"Card_Send_Transaction\", \"from_id\": \"4218196001337\", \"from_type\": \"Card\", \"to_id\": \"734580\", \"to_type\": \"Payment_Transaction\", \"directed\": false, \"attributes\": {}}, {\"e_type\": \"Card_Send_Transaction\", \"from_id\": \"4218196001337\", \"from_type\": \"Card\", \"to_id\": \"734583\", \"to_type\": \"Payment_Transaction\", \"directed\": false, \"attributes\": {}}, {\"e_type\": \"Card_Send_Transaction\", \"from_id\": \"4218196001337\", \"from_type\": \"Card\", \"to_id\": \"734577\", \"to_type\": \"Payment_Transaction\", \"directed\": false, \"attributes\": {}}, {\"e_type\": \"Card_Send_Transaction\", \"from_id\": \"4218196001337\", \"from_type\": \"Card\", \"to_id\": \"23410\", \"to_type\": \"Payment_Transaction\", \"directed\": false, \"attributes\": {}}, {\"e_type\": \"Card_Send_Transaction\", \"from_id\": \"4218196001337\", \"from_type\": \"Card\", \"to_id\": \"23412\", \"to_type\": \"Payment_Transaction\", \"directed\": false, \"attributes\": {}}, {\"e_type\": \"Card_Send_Transaction\", \"from_id\": \"4218196001337\", \"from_type\": \"Card\", \"to_id\": \"734582\", \"to_type\": \"Payment_Transaction\", \"directed\": false, \"attributes\": {}}, {\"e_type\": \"Card_Send_Transaction\", \"from_id\": \"4218196001337\", \"from_type\": \"Card\", \"to_id\": \"734579\", \"to_type\": \"Payment_Transaction\", \"directed\": false, \"attributes\": {}}]}]",
      "reasoning": "The question asks for all cards that have more than 800 transactions within a specific time period. The function 'card_has_frequent_transactions' is designed to retrieve all card numbers that have conducted more than a certain number of transactions within a specified time period. Therefore, this function is the most suitable to answer the question. The parameters 'min_createTime' and 'max_createTime' are set to '2021-04-01' and '2021-08-01' respectively to specify the time period, and 'freq' is set to 800 to specify the minimum number of transactions."
  }
}

interface Start {
  props: any;
  setState: any;
  actionProvider: any;
  actions: any;
  fullPage: any;
}

export const TransactionFraud: FC<Start> = (props) => {
  const [sdata, setsdata] = useState(JSON.parse(mockData.query_sources.result));
  const [edges, setEdges] = useState([]);
  const [dataArray, setdataArray] = useState();

  useEffect(() => {
    const setresults = sdata[1]["@@edges"];
    setEdges(setresults);
    setdataArray({
      "nodes": nodes,
      "edgez": getEdgez
    })
  }, [sdata, edges]);


  const getNodes = edges.map((d) => (
    {
      "id": `${d.to_id}`,
      "label": `${d.to_id}`
    }
  ));

  const getEdgez = edges.map((d) => (
    {
      "source": `${d.to_id}`,
      "id": `${d.to_id}`,
      "target": '0',
      "label": `${d.e_type}`
    }
  ));

  const nodes = [
    {
      id: '0',
      label: '4218196001337'
    },...getNodes
  ]

  return (
    <>
      <div className="pl-[64px]">
        <ol className="text-sm response">
          <h1 className="mb-5 text-lg">1. Financial Transactions</h1>
          <p className="block mb-5">
            Financial transactions involve the exchange of money between
            parties. Key aspects include:
          </p>
          <li>Parties Involved: The buyer and the seller.</li>
          <li>Medium of Exchange: Cash, checks, credit cards, electronic transfers.</li>
          <li>Types: Purchase of goods/services, investment, loan issuance, etc.</li>
          <li>Records: Documented through receipts, invoices, bank statements.</li>
        </ol>
      </div>

      <div style={{ position: "relative", width: '100%', height: '550px', border: '1px solid #000'}} className="my-10">
        <MyDiagram data={dataArray} />
      </div>

    </>
  );
};
