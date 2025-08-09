#!/usr/bin/env python3
"""
Test script to verify SSE handler ordering functionality
"""
import time
import threading
from src.sse_handler import SSEHandler

def test_sse_ordering():
    """Test that SSE messages are emitted in the correct order"""
    print("Testing SSE ordering functionality...")
    
    sse_handler = SSEHandler()
    
    # Track messages as they come out
    messages_received = []
    
    def collect_messages():
        """Collect messages in a separate thread"""
        for message in sse_handler.yield_messages():
            # Extract order from the message if it exists
            import json
            try:
                data = json.loads(message.replace("data: ", "").strip())
                order_info = data.get('data', {}).get('order', 'no_order') if isinstance(data.get('data'), dict) else 'no_order'
                messages_received.append((data['type'], order_info))
                print(f"Received: {data['type']} (order: {order_info})")
                
                # Stop when we get the completion message
                if data['type'] == 'complete':
                    break
            except:
                pass
    
    # Start message collection in background
    collector_thread = threading.Thread(target=collect_messages)
    collector_thread.start()
    
    # Send messages out of order to test ordering
    print("\nSending messages out of order...")
    
    # Send message with order 2 first (should be held)
    sse_handler.send('test_message', data={'order': 2, 'content': 'Second message'}, order=2)
    print("Sent order 2")
    
    # Send message with order 4 (should be held)
    sse_handler.send('test_message', data={'order': 4, 'content': 'Fourth message'}, order=4)
    print("Sent order 4")
    
    # Send message with order 1 (should be sent immediately and trigger order 2)
    sse_handler.send('test_message', data={'order': 1, 'content': 'First message'}, order=1)
    print("Sent order 1")
    
    # Send message with order 0 (should be sent immediately since it's <= current order)
    sse_handler.send('test_message', data={'order': 0, 'content': 'Zero message'}, order=0)
    print("Sent order 0")
    
    # Send message with order 3 (should be sent immediately and trigger order 4)
    sse_handler.send('test_message', data={'order': 3, 'content': 'Third message'}, order=3)
    print("Sent order 3")
    
    # Send some unordered messages (should go through immediately)
    sse_handler.send('unordered_message', data={'content': 'Unordered 1'})
    print("Sent unordered 1")
    
    sse_handler.send('unordered_message', data={'content': 'Unordered 2'})
    print("Sent unordered 2")
    
    # Wait a bit and mark complete
    time.sleep(0.1)
    sse_handler.mark_complete()
    
    # Wait for collector to finish
    collector_thread.join(timeout=5)
    
    print(f"\nReceived {len(messages_received)} messages:")
    for i, (msg_type, order_info) in enumerate(messages_received):
        print(f"  {i+1}. {msg_type} (order: {order_info})")
    
    # Check if ordered messages came in correct sequence
    ordered_messages = [(i, order) for i, (msg_type, order) in enumerate(messages_received) 
                        if msg_type == 'test_message' and isinstance(order, int)]
    
    print(f"\nOrdered messages sequence:")
    for pos, order in ordered_messages:
        print(f"  Position {pos+1}: order {order}")
    
    # Verify the order is correct
    orders = [order for pos, order in ordered_messages]
    expected_orders = [0, 1, 2, 3, 4]  # 0 should come first since it's sent with order <= current
    
    if orders == expected_orders:
        print("\n✅ SUCCESS: Messages were received in correct order!")
        return True
    else:
        print(f"\n❌ FAILED: Expected {expected_orders}, got {orders}")
        return False

if __name__ == "__main__":
    success = test_sse_ordering()
    exit(0 if success else 1)
