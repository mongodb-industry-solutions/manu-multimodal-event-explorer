import { NextResponse } from 'next/server';

/**
 * POST /api/chat/approve - Proxy approval requests to FastAPI backend
 */
export async function POST(request) {
  try {
    const body = await request.json();
    const { approval_key, approved } = body;

    if (!approval_key || typeof approved !== 'boolean') {
      return NextResponse.json(
        { error: 'Invalid request: approval_key and approved (boolean) required' },
        { status: 400 }
      );
    }

    // Forward to FastAPI backend
    const backendUrl = 'http://127.0.0.1:8000/api/chat/approve';
    
    const backendResponse = await fetch(backendUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ approval_key, approved }),
    });

    const responseData = await backendResponse.json();

    if (!backendResponse.ok) {
      return NextResponse.json(
        responseData,
        { status: backendResponse.status }
      );
    }

    return NextResponse.json(responseData);
  } catch (error) {
    console.error('[API Route] Approval error:', error);
    return NextResponse.json(
      { error: error.message },
      { status: 500 }
    );
  }
}
