import { gql } from "@apollo/client";

// Deploy a strategy into an account (creates a live UserStrategy link).
export const DEPLOY_STRATEGY = gql`
  mutation AddStrategy(
    $strategyId: String!
    $userBrokerId: String!
    $quantity: Int
  ) {
    AddStrategy(
      strategyId: $strategyId
      userBrokerId: $userBrokerId
      quantity: $quantity
    ) {
      Response
      UserStrategy {
        id
      }
    }
  }
`;

// All strategies (the page filters to isActive for the marketplace).
export const GET_MARKETPLACE = gql`
  query GetMarketplace {
    allStrategy {
      id
      name
      description
      capitalRequired
      symbol
      isActive
    }
  }
`;

// The user's accounts + which strategies are already deployed to each.
export const GET_ACCOUNTS_WITH_DEPLOYMENTS = gql`
  query GetAccountsWithDeployments {
    getuserdata {
      userbrokers {
        id
        label
        userstrategys {
          strategy {
            id
          }
        }
      }
    }
  }
`;
