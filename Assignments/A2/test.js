const readline = require('readline');

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

rl.question('Enter Command: ', (input) => {
  // Remove extra spaces between words and split the input
  const cleanedInput = input.replace(/\s+/g, ' ').trim();
  const inputArray = cleanedInput.split(' ');

  // Display the cleaned and split input
  console.log('Cleaned and split input:', inputArray);

  rl.close();
});