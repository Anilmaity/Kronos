import { ApolloClient, InMemoryCache, createHttpLink } from "@apollo/client";
import { setContext } from "@apollo/client/link/context";
import { baseUrl } from "./url";
import { STORAGE_KEYS } from "@/lib/storage";

const httpLink = createHttpLink({
  uri: `${baseUrl}/graphql/`,
});

const authLink = setContext((_, { headers }) => {
  // get the authentication token from local storage if it exists
  const userToken = localStorage.getItem(STORAGE_KEYS.token);

  if (!!userToken) {
    // return the headers to the context so httpLink can read them
    return {
      headers: {
        ...headers,
        authorization: userToken ? "JWT " + userToken : "",
      },
    };
  }
  return {
    headers: {
      ...headers,
    },
  };
});

export const client = new ApolloClient({
  link: authLink.concat(httpLink),
  cache: new InMemoryCache(),
});
