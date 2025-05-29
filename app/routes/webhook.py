from fastapi import APIRouter, status, Request, Response

from svix.webhooks import Webhook, WebhookVerificationError

router = APIRouter()

CLERK_WEBHOOK_SECRET = "whsec_egICWP120iIkTP4yN+Tpq+6Qez0q2sN0"  # Keep this safe!


@router.post("/", status_code=status.HTTP_204_NO_CONTENT)
async def webhook_handler(request: Request, response: Response):
    headers = request.headers
    payload = await request.body()

    try:
        wh = Webhook(CLERK_WEBHOOK_SECRET)
        msg = wh.verify(payload, headers)
        print("msg ", msg)
    except WebhookVerificationError as e:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
