export interface UserDetailsProps {
  id: string;
  email: string;
  firstName: string;
  lastName: string;
  isActive: boolean;
  isStaff: boolean;
  dateJoined: string;
  balance: number;
  username: string;
  profileImage: string;
  profileDescription: string;
  isSuperuser: boolean;
  todayTotalProfitLoss: number;
  clientCode: string;
}

export interface CurrencyPairProps {
  id: string;
  token: string;
  symbol: string;
  name: string;
  ltp: number;
}

export interface ActionsProps {
  id: string;
  createdAt: string;
  quantity: string;
  action: string;
  triggerValue : number;
  triggerType: string;
  actionType: string;
  createTrigger: boolean;
}

export interface UserStrategysProps {
  id: string;
  name: string;
  isActive: boolean;
  createdAt: string;
  multiplyer: string;
  deployed: string;
  strategy: StrategyProps;
  userExchange: UserExchangeSetProps;
  activePositionsCount : number;
  totalPositionCount : number;
  totalProfitLoss : number;
  positions: PositionProps[];
  clientCode: string;
}

export interface PositionProps {
  id: string;
  avgBuyPrice: number;
  createdAt: string;
  updatedAt: string;
  token: string;
  symbol: string;
  quantity: number;
  exchange: string;
  product: string;
  totalValue: number;
  currentValue: number;
  profitLoss: number;
  profitLossPercentage: number;
  ltp: number;
  date: string;
  realizedProfitLoss: number;
  triggers: TriggersProps[];
  Orders: OrderProps[];
}

export interface OrderProps {
  id: string;
  createdAt: string;
  symbol: string;
  price: string;
  condition: string;
  quantity: number;
  orderType: string;
  status: string;
  reason: string;
}


export interface UserExchangeSetProps {
  id: string;
  name: string;
  createdAt: string;
  modifiedAt: string;
  marginAvailableUsdt: string;
  marginAvailableUsdc : string;
  marginAvailable: string;
  broker: ExchangeProps;
  clientCode: string;
  isActive: boolean;
  user: UserDetailsProps;
  userstrategys: UserStrategysProps[];
  accountHolderName: string;
  label: string;
  metaAccountId: string;
  metaApiTokenLast4: string;
  hasToken: boolean;
  marginUsed?: string;
  userbrokerpositions: PositionProps[];
}

export interface ExchangeProps {
  id: string;
  name: string;
  userbrokerSet: UserExchangeSetProps[];
}



export interface StrategyProps {
  id: string;
  createdAt: string;
  name: string;
  description: string;
  isActive: boolean;
  capital: string;
  capitalRequired: string;
  monthlyReturn: string;
  drawdown: string;
  interval: string;
  symbol: string;
  actions: ActionsProps[];

}

export interface BackTestReportProps{
  id: string;
  strategyName: string;
  totalTrades: number;
  fromDate: string;
  toDate: string;
  status: string;
  totalProfitLoss: string;
  totalWinningTrades: number;
  totalLosingTrades: number;
  percentageReturn: string;
  position: PositionProps[];
  netProfitLoss: string;
  fees: string;
  netPercentageReturn: string;

}
export interface TriggersProps {
  id: string;
  name: string;
  type: string;
  params : string;
  createdAt: string;
  triggerType: string;
  triggered: boolean;
  disabled: boolean;
  triggerPrice: number;
  side: string;
  quantity: number;
  brokerAction: string;
  modifiedAt: string;
  status: string;
  exchangeOrderId: string;
}