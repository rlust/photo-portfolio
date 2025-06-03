// Test script to verify API connectivity for deletion endpoints
// Run with: node test-delete-api.js

// API endpoints
const API_BASE_URL = 'https://simplified-backend-ymcejj57ga-uc.a.run.app';
const ALTERNATE_API_URL = 'https://photoportfolio-backend-er4l5fctxq-uc.a.run.app';

// Test folder and image
const TEST_FOLDER = 'test-folder';
const TEST_IMAGE = 'test-image.jpg';

// Helper function for fetch with fallback
async function fetchWithFallback(url, options, alternateUrl = null) {
  console.log(`Attempting to fetch: ${url}`);
  try {
    const response = await fetch(url, options);
    console.log(`Response from ${url}: ${response.status}`);
    
    if (response.ok) {
      console.log('✅ Primary endpoint responded successfully');
      return response;
    }
    
    if (alternateUrl) {
      console.log(`Primary endpoint failed, trying fallback: ${alternateUrl}`);
      const alternateResponse = await fetch(alternateUrl, options);
      console.log(`Response from ${alternateUrl}: ${alternateResponse.status}`);
      
      if (alternateResponse.ok) {
        console.log('✅ Fallback endpoint responded successfully');
      } else {
        console.log('❌ Fallback endpoint failed');
      }
      
      return alternateResponse;
    }
    
    return response;
  } catch (error) {
    console.error(`❌ Error with ${url}: ${error.message}`);
    
    if (alternateUrl) {
      console.log(`Trying fallback due to error: ${alternateUrl}`);
      try {
        return await fetch(alternateUrl, options);
      } catch (fallbackError) {
        console.error(`❌ Error with fallback ${alternateUrl}: ${fallbackError.message}`);
        throw fallbackError;
      }
    }
    
    throw error;
  }
}

// Test 1: Check if delete-image endpoint is reachable
async function testImageDeletion() {
  console.log('\n🔍 TESTING IMAGE DELETION API');
  
  const deleteUrl = `${API_BASE_URL}/api/delete-image/`;
  const alternateUrl = `${ALTERNATE_API_URL}/api/delete-image/`;
  
  // Try multiple payload formats
  const payloadFormats = [
    { folder: TEST_FOLDER, filename: TEST_IMAGE },
    { folder: TEST_FOLDER, filename: `${TEST_FOLDER}/${TEST_IMAGE}` },
    { folder: TEST_FOLDER, filename: TEST_IMAGE.split('/').pop() }
  ];
  
  for (let i = 0; i < payloadFormats.length; i++) {
    console.log(`\nTesting payload format ${i+1}:`, payloadFormats[i]);
    
    const requestOptions = {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payloadFormats[i])
    };
    
    try {
      const response = await fetchWithFallback(deleteUrl, requestOptions, alternateUrl);
      let responseData;
      
      try {
        responseData = await response.json();
      } catch (e) {
        responseData = await response.text();
      }
      
      console.log('Response data:', responseData);
    } catch (error) {
      console.error(`Error testing payload format ${i+1}:`, error.message);
    }
  }
}

// Test 2: Check if folder deletion endpoint is reachable
async function testFolderDeletion() {
  console.log('\n🔍 TESTING FOLDER DELETION API');
  
  // Try both with and without URL encoding
  const tests = [
    { 
      name: 'With URL encoding',
      primaryUrl: `${API_BASE_URL}/api/folder/${encodeURIComponent(TEST_FOLDER)}`,
      alternateUrl: `${ALTERNATE_API_URL}/api/folder/${encodeURIComponent(TEST_FOLDER)}`
    },
    {
      name: 'Without URL encoding',
      primaryUrl: `${API_BASE_URL}/api/folder/${TEST_FOLDER}`,
      alternateUrl: `${ALTERNATE_API_URL}/api/folder/${TEST_FOLDER}`
    }
  ];
  
  for (const test of tests) {
    console.log(`\nTesting ${test.name}:`);
    console.log(`Primary URL: ${test.primaryUrl}`);
    console.log(`Alternate URL: ${test.alternateUrl}`);
    
    const requestOptions = { 
      method: 'DELETE',
      headers: {
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
      }
    };
    
    try {
      const response = await fetchWithFallback(test.primaryUrl, requestOptions, test.alternateUrl);
      let responseData;
      
      try {
        responseData = await response.json();
      } catch (e) {
        responseData = await response.text();
      }
      
      console.log('Response data:', responseData);
    } catch (error) {
      console.error(`Error with ${test.name}:`, error.message);
    }
  }
}

// Execute the tests
async function runTests() {
  console.log('🧪 STARTING API DELETION TESTS');
  console.log(`Primary API: ${API_BASE_URL}`);
  console.log(`Fallback API: ${ALTERNATE_API_URL}`);
  
  try {
    await testImageDeletion();
    await testFolderDeletion();
    console.log('\n✅ All tests completed');
  } catch (error) {
    console.error('\n❌ Test execution failed:', error);
  }
}

runTests();
